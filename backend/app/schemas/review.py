import uuid

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    order_id: uuid.UUID | None = None
    first_name: str = Field(min_length=1, max_length=100)
    mobile: str = Field(min_length=7, max_length=20)
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID | None
    first_name: str
    rating: int
    comment: str | None

    model_config = {"from_attributes": True}
