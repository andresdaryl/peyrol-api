from typing import Optional
from pydantic import BaseModel

class BenefitsConfigCreate(BaseModel):
    benefit_type: str
    year: str
    config_data: dict
    notes: Optional[str] = None

class BenefitsConfigUpdate(BaseModel):
    config_data: Optional[dict] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None