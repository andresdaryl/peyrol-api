from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum, Date, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base
from utils.constants import SalaryType, EmployeeStatus
import uuid

class EmployeeDB(Base):
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    contact = Column(String, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    hire_date = Column(Date, nullable=True)
    profile_image_url = Column(String, nullable=True)
    
    role = Column(String, nullable=False)
    department = Column(String)
    salary_type = Column(SQLEnum(SalaryType), nullable=False)
    salary_rate = Column(Float, nullable=False)
    allowances = Column(JSON)
    benefits = Column(JSON)
    taxes = Column(JSON)
    overtime_rate = Column(Float)
    nightshift_rate = Column(Float)
    status = Column(SQLEnum(EmployeeStatus), default=EmployeeStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    attendances = relationship("AttendanceDB", back_populates="employee", cascade="all, delete-orphan")
    leaves = relationship("LeaveDB", back_populates="employee", cascade="all, delete")
    leave_balances = relationship("LeaveBalanceDB", back_populates="employee", uselist=False, cascade="all, delete")
    payroll_entries = relationship("PayrollEntryDB", back_populates="employee", cascade="all, delete")    