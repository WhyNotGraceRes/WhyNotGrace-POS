"""Generic localized-content lookup backed by app.models.translation.Translation.

Usage: translate(db, business_id, "menu_item", item.id, "name", "hi", item.name)
Falls back to the original (default-language) value when no translation
row exists — this is what lets multi-language support be added without
duplicating backend logic per language.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.translation import Translation

# "en" is never stored — it's always the field's own value, not a
# translation row (see translate()'s early return). These are the only
# languages a translation can actually be written in; keep in sync with
# frontend SUPPORTED_LANGUAGES (src/i18n/index.ts) minus "en".
SUPPORTED_TRANSLATION_LANGUAGES = ("hi", "mr")


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


def clear_translation(
    db: Session, business_id: uuid.UUID, entity_type: str, entity_id: uuid.UUID, field_name: str, language: str,
) -> None:
    """Removes a translation row so the field falls back to the default
    language again — used when a translator blanks out a field rather than
    leaving it in an intentionally-different language."""
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
    if row is not None:
        db.delete(row)
        db.flush()
