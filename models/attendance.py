from sqlalchemy import Column, String, Float, DateTime, Date, Text, Boolean, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base
from utils.constants import ShiftType, AttendanceStatus
import uuid

class AttendanceDB(Base):
    __tablename__ = "attendance"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, ForeignKey("employees.id"))
    date = Column(Date, nullable=False)
    time_in = Column(String)
    time_out = Column(String)
    shift_type = Column(SQLEnum(ShiftType), nullable=False)
    
    regular_hours = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)
    nightshift_hours = Column(Float, default=0.0)
    
    status = Column(SQLEnum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    late_minutes = Column(Float, default=0.0)
    undertime_minutes = Column(Float, default=0.0)
    
    late_deduction = Column(Float, default=0.0)
    absent_deduction = Column(Float, default=0.0)
    undertime_deduction = Column(Float, default=0.0)
    
    is_holiday = Column(Boolean, default=False)
    holiday_id = Column(String, nullable=True)
    
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    employee = relationship("EmployeeDB", back_populates="attendances")