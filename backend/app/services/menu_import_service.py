"""Photo-based menu digitization: platform staff upload photo(s) of a
restaurant's physical menu card and get back a structured draft (category
-> items, with name/description/price) to review and correct before
anything is written to the real menu. See app/api/platform/menu_import.py
for the extract-then-publish two-step flow this backs.

Mirrors app/services/integrations/zomato_provider.py's pattern: a plain
httpx call to the external API, and a clear "not configured" error rather
than a fabricated response when ANTHROPIC_API_KEY isn't set.
"""
import base64

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.menu_import import MenuImportCategoryDraft, MenuImportItemDraft

settings = get_settings()

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
# A vision-capable model, matching the family this whole platform runs on.
EXTRACTION_MODEL = "claude-sonnet-5"

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGES = 10
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB, matching Anthropic's own per-image limit

_EXTRACTION_TOOL = {
    "name": "record_menu",
    "description": "Record every category and item read from the menu photo(s).",
    "input_schema": {
        "type": "object",
        "properties": {
            "categories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Category heading, e.g. 'Starters'"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {
                                        "type": "string",
                                        "description": "Any subtitle/ingredients line under the item name, if present",
                                    },
                                    "price": {"type": "number", "description": "Numeric price, no currency symbol"},
                                    "is_veg": {
                                        "type": "boolean",
                                        "description": "True unless the item is clearly meat/fish/egg, or marked non-veg",
                                    },
                                },
                                "required": ["name", "price", "is_veg"],
                            },
                        },
                    },
                    "required": ["name", "items"],
                },
            }
        },
        "required": ["categories"],
    },
}

_EXTRACTION_PROMPT = (
    "These photos are of one restaurant's physical menu card, possibly spanning "
    "multiple pages/photos. Read every category and item you can find and record "
    "them with the record_menu tool. Keep category and item names exactly as "
    "printed. If a price has a range or multiple sizes, use the lowest price. "
    "Skip anything you cannot confidently read rather than guessing."
)


class MenuImportNotConfigured(Exception):
    pass


def extract_menu_from_images(images: list[tuple[bytes, str]]) -> list[MenuImportCategoryDraft]:
    """images: list of (raw_bytes, content_type) tuples, one per uploaded photo."""
    if not settings.anthropic_api_key:
        raise MenuImportNotConfigured(
            "ANTHROPIC_API_KEY is not configured. Menu-photo digitization needs a real key set in the environment."
        )
    if not images:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload at least one photo.")
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Upload at most {MAX_IMAGES} photos.")

    content = []
    for raw_bytes, content_type in images:
        if content_type not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type: {content_type}. Use JPEG, PNG, WebP, or GIF.",
            )
        if len(raw_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Each photo must be under 10MB.")
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": content_type, "data": base64.b64encode(raw_bytes).decode()},
            }
        )
    content.append({"type": "text", "text": _EXTRACTION_PROMPT})

    with httpx.Client(timeout=90) as client:
        response = client.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": EXTRACTION_MODEL,
                "max_tokens": 8192,
                "tools": [_EXTRACTION_TOOL],
                "tool_choice": {"type": "tool", "name": "record_menu"},
                "messages": [{"role": "user", "content": content}],
            },
        )
        response.raise_for_status()
        data = response.json()

    tool_use = next((block for block in data.get("content", []) if block.get("type") == "tool_use"), None)
    if tool_use is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="The menu extraction model returned no structured result."
        )

    categories_raw = tool_use["input"].get("categories", [])
    return [
        MenuImportCategoryDraft(
            name=cat["name"],
            items=[
                MenuImportItemDraft(
                    name=item["name"],
                    description=item.get("description") or None,
                    price=item["price"],
                    is_veg=item.get("is_veg", True),
                )
                for item in cat.get("items", [])
                if item.get("price", 0) > 0 and item.get("name")
            ],
        )
        for cat in categories_raw
        if cat.get("name")
    ]
