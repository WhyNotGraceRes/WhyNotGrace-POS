import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    # A str, not a UUID: the synthetic "tickets are aging" notice (see
    # notification_service._stuck_kot_notice) isn't a stored row and has no
    # real id, only a stable sentinel string so the frontend can key on it.
    id: str
    type: str
    title: str
    body: str | None
    resource_type: str | None
    resource_id: uuid.UUID | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int
