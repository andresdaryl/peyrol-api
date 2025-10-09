from sqlalchemy import Column, String, Float, JSON, ForeignKey, Text, DateTime, Boolean
from datetime import datetime, timezone
from database import Base
import uuid

class BenefitsConfigDB(Base):
    """
    Store configurable benefits rates (SSS, PhilHealth, Pag-IBIG)
    Allows updating rates without code changes
    """
    __tablename__ = "benefits_config"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    benefit_type = Column(String, nullable=False, index=True)
    year = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    
    # Configuration data as JSON
    config_data = Column(JSON, nullable=False)
    
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class MandatoryContributionsDB(Base):
    """
    Store mandatory government contributions for each payroll entry.
    
    This table tracks SSS, PhilHealth, and Pag-IBIG contributions
    for both employee and employer shares.
    """
    __tablename__ = "mandatory_contributions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False, index=True)
    payroll_entry_id = Column(String, ForeignKey("payroll_entries.id"), nullable=False, index=True)
    
    # SSS Contributions
    sss_employee = Column(Float, default=0.0)
    sss_employer = Column(Float, default=0.0)
    
    # PhilHealth Contributions
    philhealth_employee = Column(Float, default=0.0)
    philhealth_employer = Column(Float, default=0.0)
    
    # Pag-IBIG Contributions
    pagibig_employee = Column(Float, default=0.0)
    pagibig_employer = Column(Float, default=0.0)
    
    # Total deductions from employee
    total_employee_contribution = Column(Float, default=0.0)
    
    # Metadata (stores calculation details as JSON)
    calculation_details = Column(JSON, default=dict)