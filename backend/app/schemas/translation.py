from pydantic import BaseModel


class TranslationOut(BaseModel):
    language: str
    name: str | None = None
    description: str | None = None


class ItemTranslationUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class CategoryTranslationUpdateRequest(BaseModel):
    name: str | None = None
