"""Generic localized-content lookup backed by app.models.translation.Translation.

Usage: translate(db, business_id, "menu_item", item.id, "name", "hi", item.name)
Falls back to the original (default-language) value when no translation
row exists — this is what lets multi-language support be added without
duplicating backend logic per language.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.translation import Translation


def translate(
    db: Session, business_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID, field_name: str,
    language: str, fallback: str,
) -> str:
    if not language or language == "en":
        return fallback
    row = (
        db.query(Translation)
        .filter(
            Translation.business_id == business_id,
            Translation.entity_type == entity_type,
            Translation.entity_id == entity_id,
            Translation.field_name == field_name,
            Translation.language == language,
        )
        .first()
    )
    return row.value if row else fallback


def upsert_translation(
    db: Session, business_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID, field_name: str,
    language: str, value: str,
) -> Translation:
    row = (
        db.query(Translation)
        .filter(
            Translation.business_id == business_id,
            Translation.entity_type == entity_type,
            Translation.entity_id == entity_id,
            Translation.field_name == field_name,
            Translation.language == language,
        )
        .first()
    )
    if row is None:
        row = Translation(
            business_id=business_id, entity_type=entity_type, entity_id=entity_id,
            field_name=field_name, language=language, value=value,
        )
        db.add(row)
    else:
        row.value = value
    db.flush()
    return row
