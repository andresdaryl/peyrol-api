from sqlalchemy import Column, String, Float, DateTime, Date, Integer, Boolean, JSON, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base
from utils.constants import PayrollRunType, PayrollRunStatus
import uuid

class PayrollRunDB(Base):
    __tablename__ = "payroll_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    type = Column(SQLEnum(PayrollRunType), nullable=False)
    status = Column(SQLEnum(PayrollRunStatus), default=PayrollRunStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PayrollEntryDB(Base):
    __tablename__ = "payroll_entries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payroll_run_id = Column(String, nullable=False, index=True)
    employee_id = Column(String, ForeignKey("employees.id"))
    employee_name = Column(String, nullable=False)
    base_pay = Column(Float, nullable=False)
    overtime_pay = Column(Float, default=0.0)
    nightshift_pay = Column(Float, default=0.0)
    allowances = Column(JSON)
    bonuses = Column(JSON)
    benefits = Column(JSON)
    deductions = Column(JSON)
    gross = Column(Float, nullable=False)
    net = Column(Float, nullable=False)
    is_finalized = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    edit_history = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    employee = relationship("EmployeeDB", back_populates="payroll_entries")


class PayslipDB(Base):
    __tablename__ = "payslips"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payroll_entry_id = Column(String, nullable=False, unique=True, index=True)
    employee_id = Column(String, nullable=False, index=True)
    pdf_base64 = Column(Text)
    is_editable = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))