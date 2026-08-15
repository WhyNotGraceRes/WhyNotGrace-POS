from pydantic import BaseModel

from app.models.enums import FeatureModule


class FeatureFlagOut(BaseModel):
    module: FeatureModule
    enabled: bool

    model_config = {"from_attributes": True}


class FeatureFlagUpdateRequest(BaseModel):
    enabled: bool
