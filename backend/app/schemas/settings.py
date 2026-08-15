import re

from pydantic import BaseModel, Field, field_validator

# 2 state digits, 10-character PAN, entity digit, 'Z', 1 check character.
GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


class BusinessSettingsOut(BaseModel):
    default_language: str
    supported_languages: str
    timezone: str
    default_tax_percent: float
    default_service_charge_percent: float
    currency: str
    gstin: str | None = None
    tax_label: str = "GST"
    tax_split_intra_state: bool = True
    fssai_number: str | None = None
    receipt_header_lines: str | None = None
    receipt_footer_text: str | None = None

    model_config = {"from_attributes": True}


class BusinessSettingsUpdateRequest(BaseModel):
    default_language: str | None = Field(default=None, max_length=10)
    supported_languages: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=64)
    default_tax_percent: float | None = Field(default=None, ge=0, le=100)
    default_service_charge_percent: float | None = Field(default=None, ge=0, le=100)
    currency: str | None = Field(default=None, max_length=8)
    gstin: str | None = Field(default=None, max_length=20)
    tax_label: str | None = Field(default=None, min_length=1, max_length=40)
    tax_split_intra_state: bool | None = None
    fssai_number: str | None = Field(default=None, max_length=30)
    receipt_header_lines: str | None = Field(default=None, max_length=500)
    receipt_footer_text: str | None = Field(default=None, max_length=500)

    @field_validator("gstin")
    @classmethod
    def _check_gstin(cls, v: str | None) -> str | None:
        """Validated on the way in, because a GSTIN typo is otherwise
        invisible: it is printed on every invoice and nothing downstream ever
        questions it, so one transposed character quietly produces months of
        non-compliant bills. An empty string normalises to None so the owner
        can clear the field.
        """
        if v is None:
            return None
        v = v.strip().upper()
        if not v:
            return None
        if not GSTIN_PATTERN.match(v):
            raise ValueError(
                "That does not look like a valid GSTIN. It should be 15 characters: "
                "a 2-digit state code, a 10-character PAN, an entity digit, 'Z', "
                "and a check character."
            )
        return v
