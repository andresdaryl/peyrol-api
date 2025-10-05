from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum
from datetime import datetime, timezone
from database import Base
from utils.constants import SalaryType, EmployeeStatus
import uuid

class EmployeeDB(Base):
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    contact = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String)
    salary_type = Column(SQLEnum(SalaryType), nullable=False)
    salary_rate = Column(Float, nullable=False)
    benefits = Column(JSON)
    taxes = Column(JSON)
    overtime_rate = Column(Float)
    nightshift_rate = Column(Float)
    status = Column(SQLEnum(EmployeeStatus), default=EmployeeStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))