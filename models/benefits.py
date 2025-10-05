from sqlalchemy import Column, String, Float, JSON, ForeignKey, Text
from datetime import datetime, timezone
from database import Base
import uuid

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