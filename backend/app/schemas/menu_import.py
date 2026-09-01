from pydantic import BaseModel, Field


class MenuImportItemDraft(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: float = Field(gt=0)
    is_veg: bool = True


class MenuImportCategoryDraft(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    items: list[MenuImportItemDraft] = Field(default_factory=list)


class MenuImportExtractResponse(BaseModel):
    categories: list[MenuImportCategoryDraft]


class MenuImportPublishRequest(BaseModel):
    categories: list[MenuImportCategoryDraft]


class MenuImportPublishResponse(BaseModel):
    categories_created: int
    items_created: int
