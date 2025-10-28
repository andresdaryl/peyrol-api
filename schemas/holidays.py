from typing import Optional
from datetime import date
from utils.constants import HolidayType
from pydantic import BaseModel

class HolidayCreate(BaseModel):
    name: str
    date: date
    holiday_type: HolidayType
    description: Optional[str] = None
    is_recurring: bool = False

class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    holiday_type: Optional[HolidayType] = None
    description: Optional[str] = None
    is_recurring: Optional[bool] = None

class HolidayResponse(BaseModel):
    id: str
    name: str
    date: date
    holiday_type: HolidayType
    description: Optional[str]
    is_recurring: bool

    class Config:
        from_attributes = True