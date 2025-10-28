from typing import Optional
from utils.constants import EmployeeStatus, SalaryType
from datetime import date
from pydantic import BaseModel, EmailStr

class EmployeeCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    contact: str
    date_of_birth: Optional[date] = None
    hire_date: Optional[date] = None
    role: str
    department: Optional[str] = None
    salary_type: SalaryType
    salary_rate: float
    allowances: Optional[dict] = None
    benefits: Optional[dict] = None
    taxes: Optional[dict] = None
    overtime_rate: Optional[float] = None
    nightshift_rate: Optional[float] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    contact: Optional[str] = None
    date_of_birth: Optional[date] = None
    hire_date: Optional[date] = None
    role: Optional[str] = None
    department: Optional[str] = None
    salary_type: Optional[SalaryType] = None
    salary_rate: Optional[float] = None
    allowances: Optional[dict] = None
    benefits: Optional[dict] = None
    taxes: Optional[dict] = None
    overtime_rate: Optional[float] = None
    nightshift_rate: Optional[float] = None
    status: Optional[EmployeeStatus] = None