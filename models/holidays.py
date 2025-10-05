from sqlalchemy import Column, String, Date, Text, Boolean, Enum as SQLEnum
from database import Base
from utils.constants import HolidayType
import uuid

class HolidayDB(Base):
    __tablename__ = "holidays"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    date = Column(Date, nullable=False, unique=True, index=True)
    holiday_type = Column(SQLEnum(HolidayType), nullable=False)
    description = Column(Text)
    is_recurring = Column(Boolean, default=False)  # For annual holidays
    
    class Config:
        indexes = [
            ('date',),  # Index for fast date lookups
        ]