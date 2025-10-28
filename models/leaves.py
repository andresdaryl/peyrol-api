from sqlalchemy import Column, String, DateTime, Date, Text, Integer, Float, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base
from utils.constants import LeaveType, LeaveStatus
import uuid

class LeaveDB(Base):
    __tablename__ = "leaves"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, ForeignKey("employees.id"))
    leave_type = Column(SQLEnum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_count = Column(Integer, nullable=False)
    reason = Column(Text)
    status = Column(SQLEnum(LeaveStatus), default=LeaveStatus.PENDING)
    
    # Approval tracking
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Attachments (medical certificate, etc.)
    attachment_url = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    employee = relationship("EmployeeDB", back_populates="leaves")


class LeaveBalanceDB(Base):
    __tablename__ = "leave_balances"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, ForeignKey("employees.id"))
    
    sick_leave_balance = Column(Float, default=15.0)
    vacation_leave_balance = Column(Float, default=15.0)
    
    year = Column(Integer, nullable=False)
    
    sick_leave_used = Column(Float, default=0.0)
    vacation_leave_used = Column(Float, default=0.0)
    
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    employee = relationship("EmployeeDB", back_populates="leave_balances")    