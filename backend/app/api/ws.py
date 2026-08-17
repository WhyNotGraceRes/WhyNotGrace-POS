"""Live-update push (see app/core/ws_manager.py). One endpoint,
`/ws?token=...`, authenticated by the same access token every REST call
uses — passed as a query param rather than an Authorization header because
browser WebSocket clients have no way to set custom headers on the
handshake request.
"""
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import TokenType, decode_token
from app.core.ws_manager import manager
from app.database.session import get_db
from app.models.user import User

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def live_updates(websocket: WebSocket, token: str, db: Session = Depends(get_db)) -> None:
    try:
        payload = decode_token(token)
    except ValueError:
        await websocket.close(code=4401)
        return

    # Same two checks get_current_user makes: a refresh token (or any
    # other non-access token) must never open this channel, and a
    # platform-staff token must never resolve to a business connection —
    # see get_current_user's own comment on why "actor": "platform" is
    # checked explicitly rather than merely tolerating a missing business.
    if payload.get("type") != TokenType.ACCESS.value or payload.get("actor") == "platform":
        await websocket.close(code=4401)
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4401)
        return

    # db (not a manually opened SessionLocal()) so this goes through the
    # same get_db dependency the rest of the app uses — tests override it
    # to point at their transactional fixture session, which a hand-rolled
    # SessionLocal() would silently bypass, seeing a different connection
    # that can't see any of that test's uncommitted data.
    user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active or user.business_id is None:
        await websocket.close(code=4401)
        return
    business_id = user.business_id

    await manager.connect(business_id, websocket)
    try:
        while True:
            # Nothing the client sends is acted on — this just keeps the
            # handler alive so a closed/dead connection surfaces promptly
            # as a WebSocketDisconnect instead of leaking a stale entry.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(business_id, websocket)
