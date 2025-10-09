"""
Benefits Calculator Service

Calculates Philippine mandatory contributions (SSS, PhilHealth, Pag-IBIG)
based on configurable rates from database (with fallback to defaults).
"""

from sqlalchemy.orm import Session
from typing import Optional
from models.benefits import BenefitsConfigDB
from utils.constants import PhilippineBenefits
from datetime import datetime


class BenefitsCalculator:
    """Calculate Philippine mandatory contributions"""
    
    @staticmethod
    def get_active_config(db: Session, benefit_type: str, year: Optional[str] = None) -> Optional[dict]:
        """Get active benefits configuration from database"""
        if year is None:
            year = str(datetime.now().year)
        
        config = db.query(BenefitsConfigDB).filter(
            BenefitsConfigDB.benefit_type == benefit_type,
            BenefitsConfigDB.year == year,
            BenefitsConfigDB.is_active == True
        ).first()
        
        return config.config_data if config else None
    
    @staticmethod
    def calculate_sss(monthly_salary: float, db: Optional[Session] = None) -> tuple[float, float]:
        """
        Calculate SSS contribution based on monthly salary.
        Uses database config if available, otherwise falls back to constants.
        """
        # Try to get config from database
        sss_config = None
        if db:
            sss_config = BenefitsCalculator.get_active_config(db, 'sss')
        
        # Use database config or fallback to constants
        sss_rates = sss_config['ranges'] if sss_config else PhilippineBenefits.SSS_RATES['ranges']
        
        # Iterate through SSS contribution table
        for rate_entry in sss_rates:
            if isinstance(rate_entry, (list, tuple)) and len(rate_entry) >= 4:
                min_sal, max_sal, total_contribution, employee_share = rate_entry
            else:
                # Handle dict format from DB
                min_sal = rate_entry.get('min_salary', 0)
                max_sal = rate_entry.get('max_salary', 0)
                total_contribution = rate_entry.get('total_contribution', 0)
                employee_share = rate_entry.get('employee_share', 0)
            
            if min_sal <= monthly_salary <= max_sal:
                employer_share = total_contribution - employee_share
                return round(employee_share, 2), round(employer_share, 2)
        
        # Default to maximum if above highest bracket
        return 500.00, 625.00
    
    @staticmethod
    def calculate_philhealth(monthly_salary: float, db: Optional[Session] = None) -> tuple[float, float]:
        """Calculate PhilHealth contribution"""
        # Try to get config from database
        philhealth_config = None
        if db:
            philhealth_config = BenefitsCalculator.get_active_config(db, 'philhealth')
        
        # Use database config or fallback to constants
        if philhealth_config:
            rate = philhealth_config.get('rate', PhilippineBenefits.PHILHEALTH_RATE)
            max_salary = philhealth_config.get('max_salary', PhilippineBenefits.PHILHEALTH_MAX_SALARY)
            min_contribution = philhealth_config.get('min_contribution', PhilippineBenefits.PHILHEALTH_MIN_CONTRIBUTION)
        else:
            rate = PhilippineBenefits.PHILHEALTH_RATE
            max_salary = PhilippineBenefits.PHILHEALTH_MAX_SALARY
            min_contribution = PhilippineBenefits.PHILHEALTH_MIN_CONTRIBUTION
        
        # Cap salary at maximum
        capped_salary = min(monthly_salary, max_salary)
        
        # Total contribution
        total_contribution = capped_salary * rate
        total_contribution = max(total_contribution, min_contribution)
        
        # Split equally
        employee_share = total_contribution / 2
        employer_share = total_contribution / 2
        
        return round(employee_share, 2), round(employer_share, 2)
    
    @staticmethod
    def calculate_pagibig(monthly_salary: float, db: Optional[Session] = None) -> tuple[float, float]:
        """Calculate Pag-IBIG contribution"""
        # Try to get config from database
        pagibig_config = None
        if db:
            pagibig_config = BenefitsCalculator.get_active_config(db, 'pagibig')
        
        # Use database config or fallback to constants
        if pagibig_config:
            employee_rate = pagibig_config.get('employee_rate', PhilippineBenefits.PAGIBIG_EMPLOYEE_RATE)
            employer_rate = pagibig_config.get('employer_rate', PhilippineBenefits.PAGIBIG_EMPLOYER_RATE)
            max_employee = pagibig_config.get('max_employee', PhilippineBenefits.PAGIBIG_MAX_EMPLOYEE)
            max_employer = pagibig_config.get('max_employer', PhilippineBenefits.PAGIBIG_MAX_EMPLOYER)
        else:
            employee_rate = PhilippineBenefits.PAGIBIG_EMPLOYEE_RATE
            employer_rate = PhilippineBenefits.PAGIBIG_EMPLOYER_RATE
            max_employee = PhilippineBenefits.PAGIBIG_MAX_EMPLOYEE
            max_employer = PhilippineBenefits.PAGIBIG_MAX_EMPLOYER
        
        # Calculate contributions
        employee_contribution = min(monthly_salary * employee_rate, max_employee)
        employer_contribution = min(monthly_salary * employer_rate, max_employer)
        
        return round(employee_contribution, 2), round(employer_contribution, 2)
    
    @staticmethod
    def calculate_all_contributions(monthly_salary: float, db: Optional[Session] = None) -> dict:
        """
        Calculate all mandatory contributions for a given monthly salary.
        Now accepts optional db session to use configurable rates.
        """
        # Calculate each contribution type
        sss_ee, sss_er = BenefitsCalculator.calculate_sss(monthly_salary, db)
        philhealth_ee, philhealth_er = BenefitsCalculator.calculate_philhealth(monthly_salary, db)
        pagibig_ee, pagibig_er = BenefitsCalculator.calculate_pagibig(monthly_salary, db)
        
        # Calculate totals
        total_employee = sss_ee + philhealth_ee + pagibig_ee
        total_employer = sss_er + philhealth_er + pagibig_er
        
        return {
            'sss': {
                'employee': round(sss_ee, 2),
                'employer': round(sss_er, 2),
                'total': round(sss_ee + sss_er, 2)
            },
            'philhealth': {
                'employee': round(philhealth_ee, 2),
                'employer': round(philhealth_er, 2),
                'total': round(philhealth_ee + philhealth_er, 2)
            },
            'pagibig': {
                'employee': round(pagibig_ee, 2),
                'employer': round(pagibig_er, 2),
                'total': round(pagibig_ee + pagibig_er, 2)
            },
            'total_employee': round(total_employee, 2),
            'total_employer': round(total_employer, 2),
            'grand_total': round(total_employee + total_employer, 2)
        }