from sqlalchemy import Column, String, Float, JSON, DateTime, Boolean, Text
from datetime import datetime, timezone
from database import Base
import uuid

class TaxConfigDB(Base):
    """
    Store Philippine withholding tax tables (BIR Tax Tables)
    """
    __tablename__ = "tax_config"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tax_type = Column(String, nullable=False, index=True)
    year = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    
    # Tax brackets and rates as JSON
    # Example: [{"min": 0, "max": 250000, "rate": 0, "base_tax": 0}, ...]
    tax_brackets = Column(JSON, nullable=False)
    
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))