import re
import uuid

from sqlalchemy.orm import Session


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "business"


def unique_slug(db: Session, model, name: str) -> str:
    base = slugify(name)
    candidate = base
    suffix = 1
    while db.query(model).filter(model.slug == candidate).first() is not None:
        suffix += 1
        candidate = f"{base}-{suffix}"
        if suffix > 10000:
            candidate = f"{base}-{uuid.uuid4().hex[:8]}"
            break
    return candidate
