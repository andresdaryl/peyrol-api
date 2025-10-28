from typing import Optional
from datetime import date
from utils.constants import ShiftType
from pydantic import BaseModel

class AttendanceCreate(BaseModel):
    employee_id: str
    date: date
    time_in: Optional[str] = None
    time_out: Optional[str] = None
    shift_type: ShiftType
    overtime_hours: float = 0.0
    nightshift_hours: float = 0.0
    notes: Optional[str] = None
    expected_time_in: str = "08:00"
    expected_time_out: str = "17:00"

class AttendanceUpdate(BaseModel):
    date: Optional[str] = None
    time_in: Optional[str] = None
    time_out: Optional[str] = None
    shift_type: Optional[ShiftType] = None
    overtime_hours: Optional[float] = None
    nightshift_hours: Optional[float] = None
    notes: Optional[str] = None