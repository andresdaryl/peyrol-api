"""
Benefits Calculator Service

Calculates Philippine mandatory contributions (SSS, PhilHealth, Pag-IBIG)
based on 2024 contribution tables and rates.
"""

from utils.constants import PhilippineBenefits


class BenefitsCalculator:
    """Calculate Philippine mandatory contributions"""
    
    @staticmethod
    def calculate_sss(monthly_salary: float) -> tuple[float, float]:
        """
        Calculate SSS contribution based on monthly salary.
        
        Args:
            monthly_salary: Employee's monthly salary in PHP
            
        Returns:
            tuple: (employee_share, employer_share) in PHP
            
        Example:
            >>> BenefitsCalculator.calculate_sss(15000)
            (300.00, 375.00)
        """
        # Iterate through SSS contribution table
        for min_sal, max_sal, total_contribution, employee_share in PhilippineBenefits.SSS_RATES['ranges']:
            if min_sal <= monthly_salary <= max_sal:
                employer_share = total_contribution - employee_share
                return round(employee_share, 2), round(employer_share, 2)
        
        # Default to maximum if above highest bracket (₱29,750+)
        return 500.00, 625.00
    
    @staticmethod
    def calculate_philhealth(monthly_salary: float) -> tuple[float, float]:
        """
        Calculate PhilHealth contribution based on monthly salary.
        
        PhilHealth contribution is 4% of monthly salary (up to ₱80,000 cap),
        split equally between employee and employer (2% each).
        
        Args:
            monthly_salary: Employee's monthly salary in PHP
            
        Returns:
            tuple: (employee_share, employer_share) in PHP
            
        Example:
            >>> BenefitsCalculator.calculate_philhealth(25000)
            (500.00, 500.00)
        """
        # Cap salary at maximum (₱80,000)
        capped_salary = min(monthly_salary, PhilippineBenefits.PHILHEALTH_MAX_SALARY)
        
        # Total contribution is 4% of capped salary
        total_contribution = capped_salary * PhilippineBenefits.PHILHEALTH_RATE
        
        # Ensure minimum contribution (₱400 total = ₱200 each)
        total_contribution = max(total_contribution, PhilippineBenefits.PHILHEALTH_MIN_CONTRIBUTION)
        
        # Split equally between employee and employer
        employee_share = total_contribution / 2
        employer_share = total_contribution / 2
        
        return round(employee_share, 2), round(employer_share, 2)
    
    @staticmethod
    def calculate_pagibig(monthly_salary: float) -> tuple[float, float]:
        """
        Calculate Pag-IBIG contribution based on monthly salary.
        
        Both employee and employer contribute 2% of monthly salary,
        capped at ₱100 each.
        
        Args:
            monthly_salary: Employee's monthly salary in PHP
            
        Returns:
            tuple: (employee_share, employer_share) in PHP
            
        Example:
            >>> BenefitsCalculator.calculate_pagibig(8000)
            (100.00, 100.00)
        """
        # Employee contribution: 2% of salary (capped at ₱100)
        employee_contribution = monthly_salary * PhilippineBenefits.PAGIBIG_EMPLOYEE_RATE
        employee_contribution = min(employee_contribution, PhilippineBenefits.PAGIBIG_MAX_EMPLOYEE)
        
        # Employer contribution: 2% of salary (capped at ₱100)
        employer_contribution = monthly_salary * PhilippineBenefits.PAGIBIG_EMPLOYER_RATE
        employer_contribution = min(employer_contribution, PhilippineBenefits.PAGIBIG_MAX_EMPLOYER)
        
        return round(employee_contribution, 2), round(employer_contribution, 2)
    
    @staticmethod
    def calculate_all_contributions(monthly_salary: float) -> dict:
        """
        Calculate all mandatory contributions for a given monthly salary.
        
        This is the main method used by the payroll calculator to get
        complete contribution breakdown.
        
        Args:
            monthly_salary: Employee's monthly salary in PHP
            
        Returns:
            dict: Complete breakdown of all contributions
            
        Example:
            >>> BenefitsCalculator.calculate_all_contributions(20000)
            {
                'sss': {'employee': 400.00, 'employer': 500.00},
                'philhealth': {'employee': 400.00, 'employer': 400.00},
                'pagibig': {'employee': 100.00, 'employer': 100.00},
                'total_employee': 900.00,
                'total_employer': 1000.00,
                'grand_total': 1900.00
            }
        """
        # Calculate each contribution type
        sss_ee, sss_er = BenefitsCalculator.calculate_sss(monthly_salary)
        philhealth_ee, philhealth_er = BenefitsCalculator.calculate_philhealth(monthly_salary)
        pagibig_ee, pagibig_er = BenefitsCalculator.calculate_pagibig(monthly_salary)
        
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
    
    @staticmethod
    def get_contribution_summary(monthly_salary: float) -> str:
        """
        Get a human-readable summary of contributions.
        
        Useful for logging or displaying to users.
        
        Args:
            monthly_salary: Employee's monthly salary in PHP
            
        Returns:
            str: Formatted contribution summary
        """
        contributions = BenefitsCalculator.calculate_all_contributions(monthly_salary)
        
        summary = f"""
Mandatory Contributions Summary for Salary: ₱{monthly_salary:,.2f}
{'='*60}
SSS:
  Employee: ₱{contributions['sss']['employee']:,.2f}
  Employer: ₱{contributions['sss']['employer']:,.2f}
  Total:    ₱{contributions['sss']['total']:,.2f}

PhilHealth:
  Employee: ₱{contributions['philhealth']['employee']:,.2f}
  Employer: ₱{contributions['philhealth']['employer']:,.2f}
  Total:    ₱{contributions['philhealth']['total']:,.2f}

Pag-IBIG:
  Employee: ₱{contributions['pagibig']['employee']:,.2f}
  Employer: ₱{contributions['pagibig']['employer']:,.2f}
  Total:    ₱{contributions['pagibig']['total']:,.2f}

TOTAL DEDUCTIONS FROM EMPLOYEE: ₱{contributions['total_employee']:,.2f}
TOTAL EMPLOYER CONTRIBUTION:    ₱{contributions['total_employer']:,.2f}
GRAND TOTAL:                    ₱{contributions['grand_total']:,.2f}
{'='*60}
        """
        return summary.strip()


# Example usage and testing
if __name__ == "__main__":
    # Test calculations for different salary levels
    test_salaries = [5000, 10000, 15000, 20000, 25000, 30000, 50000, 80000]
    
    print("Philippine Mandatory Contributions Calculator - 2024 Rates")
    print("="*70)
    
    for salary in test_salaries:
        print(f"\nMonthly Salary: ₱{salary:,.2f}")
        contributions = BenefitsCalculator.calculate_all_contributions(salary)
        print(f"  SSS:        Employee ₱{contributions['sss']['employee']:>7,.2f}  |  Employer ₱{contributions['sss']['employer']:>7,.2f}")
        print(f"  PhilHealth: Employee ₱{contributions['philhealth']['employee']:>7,.2f}  |  Employer ₱{contributions['philhealth']['employer']:>7,.2f}")
        print(f"  Pag-IBIG:   Employee ₱{contributions['pagibig']['employee']:>7,.2f}  |  Employer ₱{contributions['pagibig']['employer']:>7,.2f}")
        print(f"  TOTAL:      Employee ₱{contributions['total_employee']:>7,.2f}  |  Employer ₱{contributions['total_employer']:>7,.2f}")
        print(f"  Employee Net Deduction: ₱{contributions['total_employee']:,.2f}")