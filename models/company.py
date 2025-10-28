from sqlalchemy import Column, String, DateTime, Text
from datetime import datetime, timezone
from database import Base

class CompanyProfileDB(Base):
    __tablename__ = "company_profile"
    
    id = Column(String, primary_key=True, default="company_001")  # Single row
    company_name = Column(String, nullable=False)
    address = Column(Text, nullable=True)
    contact_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)  # TIN or similar
    logo_url = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))