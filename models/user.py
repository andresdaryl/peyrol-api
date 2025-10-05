from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from datetime import datetime, timezone
from database import Base
from utils.constants import UserRole
from sqlalchemy import Enum as SQLEnum
import uuid

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))