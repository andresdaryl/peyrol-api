from typing import Optional
from datetime import date, datetime
from utils.constants import LeaveType, LeaveStatus
from pydantic import BaseModel

class LeaveCreate(BaseModel):
    employee_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None
    attachment_url: Optional[str] = None

class LeaveUpdate(BaseModel):
    status: Optional[LeaveStatus] = None
    rejection_reason: Optional[str] = None

class LeaveResponse(BaseModel):
    id: str
    employee_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    days_count: int
    reason: Optional[str]
    status: LeaveStatus
    approved_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class LeaveCreditsAssignment(BaseModel):
    employee_id: str
    sick_leave: float
    vacation_leave: float
    reason: Optional[str] = None      