"""Authenticating an inbound partner-site request.

A partner site is not a logged-in user, so there is no JWT. It presents:

    X-Partner-Key        the channel's public key_id
    X-Partner-Timestamp  unix seconds, when the request was signed
    X-Partner-Nonce      a single-use random string
    X-Partner-Signature  hex HMAC-SHA256 over the canonical string below

The signed string is:

    {METHOD}\\n{path}\\n{timestamp}\\n{nonce}\\n{sha256hex(body)}

Signing the method and path as well as the body matters: a signature over
the body alone could be lifted from one endpoint and replayed against a
different one that happens to accept the same shape. Hashing the body
rather than signing it directly keeps the signed string small and fixed
regardless of payload size.

Three separate protections, because each covers a different attack:

* The HMAC proves the sender holds the shared secret. The secret never
  crosses the wire — only a signature derived from it does.
* The timestamp window bounds how long a captured request stays usable at
  all, which is also what bounds the nonce table's growth.
* The nonce makes replay impossible inside that window, enforced by a
  unique constraint rather than a read-then-write check, so two concurrent
  replays race to insert and the database refuses the loser.

What this deliberately does NOT do is grant general API access. A partner
credential authenticates only the partner endpoints and resolves exactly one
business_id; it is never accepted by get_current_user and carries no role,
so a leaked key cannot read customers, reports, payments, staff, or any
other tenant's data. The blast radius of a compromised key is "can place
real orders, at real prices, for one business" — which is recoverable by
revoking it, and visible in the audit log either way.
"""
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_text
from app.core.security import constant_time_compare
from app.database.session import get_db
from app.models.enums import FeatureModule
from app.models.partner import PartnerChannel, PartnerRequestNonce

# One generic message for every authentication failure. Distinguishing
# "unknown key" from "bad signature" from "revoked" would let a caller probe
# which key ids exist; the server logs the real reason, the caller gets one
# opaque answer.
_AUTH_FAILED = "Partner authentication failed"

# Compared against when the key id is unknown, so a lookup miss does roughly
# the same work as a real verification instead of returning noticeably faster.
_DUMMY_SECRET = "0" * 64


def _reject() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_AUTH_FAILED)


def build_signing_string(*, method: str, path: str, timestamp: str, nonce: str, body: bytes) -> str:
    """The exact string both sides HMAC. Exported so partner-side code and
    the test suite derive it from this one definition rather than keeping
    their own copy that can silently drift."""
    body_hash = hashlib.sha256(body).hexdigest()
    return f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"


def sign(secret: str, signing_string: str) -> str:
    return hmac.new(secret.encode(), signing_string.encode(), hashlib.sha256).hexdigest()


def _check_timestamp(raw: str) -> None:
    try:
        sent_at = int(raw)
    except (TypeError, ValueError):
        raise _reject()
    skew = get_settings().partner_signature_max_skew_seconds
    # Absolute difference, so a clock running fast is rejected too — a
    # far-future timestamp would otherwise stay replayable indefinitely.
    if abs(int(time.time()) - sent_at) > skew:
        raise _reject()


def _consume_nonce(db: Session, channel_id: uuid.UUID, nonce: str) -> None:
    """Records the nonce, rejecting a replay.

    Uses a nested transaction so that the IntegrityError from a duplicate
    rolls back only this INSERT — the caller's surrounding transaction (and
    the session it is using) stays usable, which matters because this runs
    inside request handling, not at its edge.
    """
    try:
        with db.begin_nested():
            db.add(PartnerRequestNonce(channel_id=channel_id, nonce=nonce))
            db.flush()
    except IntegrityError:
        raise _reject()


def prune_expired_nonces(db: Session, *, older_than_seconds: int | None = None) -> int:
    """Drops nonces old enough that their requests would already fail the
    timestamp check, so the table cannot grow without bound. Safe to call
    from any maintenance job; it lives here so the retention rule sits next
    to the rule that determines it."""
    window = older_than_seconds or get_settings().partner_signature_max_skew_seconds
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window * 2)
    return db.query(PartnerRequestNonce).filter(PartnerRequestNonce.created_at < cutoff).delete()


def _require_partner_feature(db: Session, business_id: uuid.UUID) -> None:
    """The second gate. Issuing a credential is one deliberate act by an
    owner; enabling inbound submission for the business is another. Both
    must hold, so a credential issued months ago stops working the moment
    the module is switched off — without anyone having to remember which
    keys exist."""
    from app.models.feature_flag import FeatureFlag

    flag = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.business_id == business_id, FeatureFlag.module == FeatureModule.PARTNER_CHANNEL)
        .first()
    )
    if flag is None or not flag.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The 'PARTNER_CHANNEL' module is not enabled for this business",
        )


def authenticate_partner_request(
    *,
    db: Session,
    method: str,
    path: str,
    key_id: str | None,
    timestamp: str | None,
    nonce: str | None,
    signature: str | None,
    body: bytes,
) -> PartnerChannel:
    """Returns the authenticated channel, or raises 401/403.

    The returned channel's business_id is the ONLY tenant scope the caller
    receives. Nothing downstream may read a business id from the request
    body — same rule as app/core/dependencies.py enforces for staff JWTs.
    """
    if not key_id or not timestamp or not nonce or not signature:
        raise _reject()
    # Bounded before any work, so oversized headers can't be used to make
    # the server hash or store something large.
    if len(key_id) > 64 or len(nonce) > 128 or len(signature) > 128:
        raise _reject()

    _check_timestamp(timestamp)

    signing_string = build_signing_string(
        method=method, path=path, timestamp=timestamp, nonce=nonce, body=body
    )

    channel = db.query(PartnerChannel).filter(PartnerChannel.key_id == key_id).first()
    if channel is None:
        constant_time_compare(sign(_DUMMY_SECRET, signing_string), signature)
        raise _reject()
    if not channel.is_active or channel.revoked_at is not None:
        constant_time_compare(sign(_DUMMY_SECRET, signing_string), signature)
        raise _reject()

    try:
        secret = decrypt_text(channel.secret_encrypted)
    except Exception:  # noqa: BLE001 - an undecryptable secret is an auth failure, not a 500
        raise _reject()

    if not constant_time_compare(sign(secret, signing_string), signature):
        raise _reject()

    # Only now that the signature is known good is it worth writing to the
    # database — otherwise an unauthenticated flood could fill the nonce
    # table with junk.
    _consume_nonce(db, channel.id, nonce)

    _require_partner_feature(db, channel.business_id)

    channel.last_used_at = datetime.now(timezone.utc)
    return channel


async def get_partner_channel(
    request: Request,
    x_partner_key: str | None = Header(default=None, alias="X-Partner-Key"),
    x_partner_timestamp: str | None = Header(default=None, alias="X-Partner-Timestamp"),
    x_partner_nonce: str | None = Header(default=None, alias="X-Partner-Nonce"),
    x_partner_signature: str | None = Header(default=None, alias="X-Partner-Signature"),
    db: Session = Depends(get_db),
) -> PartnerChannel:
    """FastAPI dependency for partner-authenticated routes.

    Async specifically so the raw body can be awaited — the signature covers
    the exact bytes received, which is the only way to be sure the payload
    that was signed is the payload that gets parsed. Re-serializing a parsed
    model and signing that instead would let a difference in JSON formatting
    between the two sides break every request, or worse, let two different
    payloads verify against one signature.
    """
    body = await request.body()
    return authenticate_partner_request(
        db=db,
        method=request.method,
        path=request.url.path,
        key_id=x_partner_key,
        timestamp=x_partner_timestamp,
        nonce=x_partner_nonce,
        signature=x_partner_signature,
        body=body,
    )
