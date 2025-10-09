"""
Initialize default benefits and tax configurations
Run this once to populate the database with 2024/2025 rates
Usage: python scripts/initialize_benefits_tax.py
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models.benefits import BenefitsConfigDB
from models.taxes import TaxConfigDB
from utils.constants import PhilippineBenefits
import uuid

def initialize_sss_config(db: Session, year: str):
    """Initialize SSS configuration"""
    existing = db.query(BenefitsConfigDB).filter(
        BenefitsConfigDB.benefit_type == 'sss',
        BenefitsConfigDB.year == year
    ).first()
    
    if existing:
        print(f"SSS config for {year} already exists")
        return
    
    # Convert tuple ranges to dict format for JSON storage
    sss_ranges = []
    for min_sal, max_sal, total_contrib, employee_share in PhilippineBenefits.SSS_RATES['ranges']:
        sss_ranges.append({
            "min_salary": min_sal,
            "max_salary": max_sal,
            "total_contribution": total_contrib,
            "employee_share": employee_share
        })
    
    config = BenefitsConfigDB(
        id=str(uuid.uuid4()),
        benefit_type='sss',
        year=year,
        is_active=True,
        config_data={'ranges': sss_ranges},
        notes=f'SSS contribution table for {year}'
    )
    
    db.add(config)
    print(f"✅ Created SSS config for {year}")

def initialize_philhealth_config(db: Session, year: str):
    """Initialize PhilHealth configuration"""
    existing = db.query(BenefitsConfigDB).filter(
        BenefitsConfigDB.benefit_type == 'philhealth',
        BenefitsConfigDB.year == year
    ).first()
    
    if existing:
        print(f"PhilHealth config for {year} already exists")
        return
    
    config = BenefitsConfigDB(
        id=str(uuid.uuid4()),
        benefit_type='philhealth',
        year=year,
        is_active=True,
        config_data={
            'rate': PhilippineBenefits.PHILHEALTH_RATE,
            'max_salary': PhilippineBenefits.PHILHEALTH_MAX_SALARY,
            'min_contribution': PhilippineBenefits.PHILHEALTH_MIN_CONTRIBUTION
        },
        notes=f'PhilHealth contribution rates for {year}'
    )
    
    db.add(config)
    print(f"✅ Created PhilHealth config for {year}")

def initialize_pagibig_config(db: Session, year: str):
    """Initialize Pag-IBIG configuration"""
    existing = db.query(BenefitsConfigDB).filter(
        BenefitsConfigDB.benefit_type == 'pagibig',
        BenefitsConfigDB.year == year
    ).first()
    
    if existing:
        print(f"Pag-IBIG config for {year} already exists")
        return
    
    config = BenefitsConfigDB(
        id=str(uuid.uuid4()),
        benefit_type='pagibig',
        year=year,
        is_active=True,
        config_data={
            'employee_rate': PhilippineBenefits.PAGIBIG_EMPLOYEE_RATE,
            'employer_rate': PhilippineBenefits.PAGIBIG_EMPLOYER_RATE,
            'max_employee': PhilippineBenefits.PAGIBIG_MAX_EMPLOYEE,
            'max_employer': PhilippineBenefits.PAGIBIG_MAX_EMPLOYER
        },
        notes=f'Pag-IBIG contribution rates for {year}'
    )
    
    db.add(config)
    print(f"✅ Created Pag-IBIG config for {year}")

def initialize_tax_config(db: Session, year: str):
    """Initialize tax configuration"""
    existing = db.query(TaxConfigDB).filter(
        TaxConfigDB.tax_type == 'withholding_tax',
        TaxConfigDB.year == year
    ).first()
    
    if existing:
        print(f"Tax config for {year} already exists")
        return
    
    # TRAIN Law tax brackets (2024-2025)
    tax_brackets = [
        {"min": 0, "max": 250000, "rate": 0.0, "base_tax": 0},
        {"min": 250001, "max": 400000, "rate": 0.15, "base_tax": 0},
        {"min": 400001, "max": 800000, "rate": 0.20, "base_tax": 22500},
        {"min": 800001, "max": 2000000, "rate": 0.25, "base_tax": 102500},
        {"min": 2000001, "max": 8000000, "rate": 0.30, "base_tax": 402500},
        {"min": 8000001, "max": 999999999, "rate": 0.35, "base_tax": 2202500}
    ]
    
    config = TaxConfigDB(
        id=str(uuid.uuid4()),
        tax_type='withholding_tax',
        year=year,
        is_active=True,
        tax_brackets=tax_brackets,
        notes=f'TRAIN Law withholding tax table for {year}'
    )
    
    db.add(config)
    print(f"✅ Created tax config for {year}")

def main():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        print("\n🔧 Initializing Benefits and Tax Configurations...")
        print("="*60)
        
        # Initialize for 2024 and 2025
        for year in ['2024', '2025']:
            print(f"\n📅 Year: {year}")
            initialize_sss_config(db, year)
            initialize_philhealth_config(db, year)
            initialize_pagibig_config(db, year)
            initialize_tax_config(db, year)
        
        db.commit()
        
        print("\n" + "="*60)
        print("✅ All configurations initialized successfully!")
        print("\nYou can now manage rates through the API:")
        print("  - GET  /api/benefits-config")
        print("  - POST /api/benefits-config")
        print("  - GET  /api/tax-config")
        print("  - POST /api/tax-config")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()