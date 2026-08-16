"""Audit logging. Call record() from within the same DB transaction as the
action being audited so the log entry and the change succeed or fail
together.
"""
import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record(
    db: Session,
    *,
    action: str,
    business_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    platform_user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        business_id=business_id,
        user_id=user_id,
        platform_user_id=platform_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip_address,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(entry)
    db.flush()
    return entry
