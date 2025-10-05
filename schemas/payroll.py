from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from utils.constants import PayrollRunType, PayrollRunStatus

class PayrollRunCreate(BaseModel):
    start_date: date
    end_date: date
    type: PayrollRunType

class PayrollRunUpdate(BaseModel):
    status: Optional[PayrollRunStatus] = None

class PayrollRun(BaseModel):
    id: str
    start_date: date
    end_date: date
    type: PayrollRunType
    status: PayrollRunStatus
    created_at: datetime

    class Config:
        from_attributes = True

class PayrollEntryUpdate(BaseModel):
    base_pay: Optional[float] = None
    overtime_pay: Optional[float] = None
    nightshift_pay: Optional[float] = None
    bonuses: Optional[Dict[str, float]] = None
    benefits: Optional[Dict[str, float]] = None
    deductions: Optional[Dict[str, float]] = None

class PayrollEntry(BaseModel):
    id: str
    payroll_run_id: str
    employee_id: str
    employee_name: str
    base_pay: float
    overtime_pay: float
    nightshift_pay: float
    bonuses: Optional[Dict[str, float]] = None
    benefits: Optional[Dict[str, float]] = None
    deductions: Optional[Dict[str, float]] = None
    gross: float
    net: float
    is_finalized: bool
    version: int
    edit_history: List[Dict[str, Any]] = []
    created_at: datetime

    class Config:
        from_attributes = True