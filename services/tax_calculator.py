"""
Tax Calculator Service

Calculates Philippine withholding tax based on BIR tax tables.
"""

from sqlalchemy.orm import Session
from typing import Optional
from models.taxes import TaxConfigDB
from datetime import datetime


class TaxCalculator:
    """Calculate Philippine withholding tax"""
    
    # Default 2024 Tax Brackets (TRAIN Law) - Annual basis
    DEFAULT_TAX_BRACKETS = [
        {"min": 0, "max": 250000, "rate": 0.0, "base_tax": 0},
        {"min": 250001, "max": 400000, "rate": 0.15, "base_tax": 0},
        {"min": 400001, "max": 800000, "rate": 0.20, "base_tax": 22500},
        {"min": 800001, "max": 2000000, "rate": 0.25, "base_tax": 102500},
        {"min": 2000001, "max": 8000000, "rate": 0.30, "base_tax": 402500},
        {"min": 8000001, "max": float('inf'), "rate": 0.35, "base_tax": 2202500}
    ]
    
    @staticmethod
    def get_active_tax_config(db: Session, year: Optional[str] = None) -> Optional[list]:
        """Get active tax configuration from database"""
        if year is None:
            year = str(datetime.now().year)
        
        config = db.query(TaxConfigDB).filter(
            TaxConfigDB.tax_type == 'withholding_tax',
            TaxConfigDB.year == year,
            TaxConfigDB.is_active == True
        ).first()
        
        return config.tax_brackets if config else None
    
    @staticmethod
    def calculate_annual_tax(annual_taxable_income: float, db: Optional[Session] = None) -> float:
        """
        Calculate annual withholding tax based on taxable income.
        Uses database config if available, otherwise falls back to defaults.
        """
        # Try to get config from database
        tax_brackets = None
        if db:
            tax_brackets = TaxCalculator.get_active_tax_config(db)
        
        # Use database config or fallback to defaults
        if not tax_brackets:
            tax_brackets = TaxCalculator.DEFAULT_TAX_BRACKETS
        
        # Find applicable bracket
        for bracket in tax_brackets:
            min_income = bracket.get('min', 0)
            max_income = bracket.get('max', float('inf'))
            
            if min_income <= annual_taxable_income <= max_income:
                base_tax = bracket.get('base_tax', 0)
                rate = bracket.get('rate', 0)
                
                # Tax = base_tax + (income_over_min * rate)
                income_over_min = annual_taxable_income - min_income
                tax = base_tax + (income_over_min * rate)
                
                return round(tax, 2)
        
        return 0.0
    
    @staticmethod
    def calculate_monthly_tax(
        monthly_gross: float,
        mandatory_contributions: float,
        other_deductions: float = 0.0,
        db: Optional[Session] = None
    ) -> float:
        """
        Calculate monthly withholding tax.
        
        Formula:
        1. Annualized gross = monthly_gross * 12
        2. Annualized deductions = (mandatory_contributions + other_deductions) * 12
        3. Annualized taxable income = annualized_gross - annualized_deductions
        4. Annual tax = calculate based on tax brackets
        5. Monthly tax = annual_tax / 12
        """
        # Annualize
        annual_gross = monthly_gross * 12
        annual_deductions = (mandatory_contributions + other_deductions) * 12
        annual_taxable_income = annual_gross - annual_deductions
        
        # Calculate annual tax
        annual_tax = TaxCalculator.calculate_annual_tax(annual_taxable_income, db)
        
        # Convert to monthly
        monthly_tax = annual_tax / 12
        
        return round(monthly_tax, 2)
    
    @staticmethod
    def calculate_tax_for_payroll(
        gross_pay: float,
        mandatory_contributions: dict,
        db: Optional[Session] = None
    ) -> dict:
        """
        Calculate tax for payroll entry.
        Returns detailed breakdown.
        """
        # Get total mandatory contributions
        total_contributions = mandatory_contributions.get('total_employee', 0)
        
        # Calculate monthly tax
        monthly_tax = TaxCalculator.calculate_monthly_tax(
            monthly_gross=gross_pay,
            mandatory_contributions=total_contributions,
            db=db
        )
        
        return {
            'withholding_tax': monthly_tax,
            'taxable_income': gross_pay - total_contributions,
            'tax_exempt_contributions': total_contributions
        }