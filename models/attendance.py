from sqlalchemy import Column, String, Float, DateTime, Date, Text, Boolean, Enum as SQLEnum
from datetime import datetime, timezone
from database import Base
from utils.constants import ShiftType
import uuid

class AttendanceDB(Base):
    __tablename__ = "attendance"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, nullable=False, index=True)
    date = Column(Date, nullable=False)
    time_in = Column(String, nullable=False)
    time_out = Column(String, nullable=False)
    shift_type = Column(SQLEnum(ShiftType), nullable=False)
    overtime_hours = Column(Float, default=0.0)
    nightshift_hours = Column(Float, default=0.0)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))