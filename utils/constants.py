from enum import Enum

class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"

class SalaryType(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"

class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class PayrollRunType(str, Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "bi-weekly"
    MONTHLY = "monthly"

class PayrollRunStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    ARCHIVED = "archived"

class ShiftType(str, Enum):
    DAY = "day"
    NIGHT = "night"
    MIXED = "mixed"


# Philippine Mandatory Contributions (2024 rates)
class PhilippineBenefits:
    """
    Philippine mandatory contribution rates and tables for 2024.
    
    Sources:
    - SSS: Social Security System Contribution Schedule
    - PhilHealth: Philippine Health Insurance Corporation
    - Pag-IBIG: Home Development Mutual Fund
    """
    
    # SSS Contribution Table (monthly salary brackets)
    # Format: (min_salary, max_salary, total_contribution, employee_share)
    SSS_RATES = {
        'ranges': [
            (0, 4249.99, 180.00, 80.00),
            (4250, 4749.99, 202.50, 90.00),
            (4750, 5249.99, 225.00, 100.00),
            (5250, 5749.99, 247.50, 110.00),
            (5750, 6249.99, 270.00, 120.00),
            (6250, 6749.99, 292.50, 130.00),
            (6750, 7249.99, 315.00, 140.00),
            (7250, 7749.99, 337.50, 150.00),
            (7750, 8249.99, 360.00, 160.00),
            (8250, 8749.99, 382.50, 170.00),
            (8750, 9249.99, 405.00, 180.00),
            (9250, 9749.99, 427.50, 190.00),
            (9750, 10249.99, 450.00, 200.00),
            (10250, 10749.99, 472.50, 210.00),
            (10750, 11249.99, 495.00, 220.00),
            (11250, 11749.99, 517.50, 230.00),
            (11750, 12249.99, 540.00, 240.00),
            (12250, 12749.99, 562.50, 250.00),
            (12750, 13249.99, 585.00, 260.00),
            (13250, 13749.99, 607.50, 270.00),
            (13750, 14249.99, 630.00, 280.00),
            (14250, 14749.99, 652.50, 290.00),
            (14750, 15249.99, 675.00, 300.00),
            (15250, 15749.99, 697.50, 310.00),
            (15750, 16249.99, 720.00, 320.00),
            (16250, 16749.99, 742.50, 330.00),
            (16750, 17249.99, 765.00, 340.00),
            (17250, 17749.99, 787.50, 350.00),
            (17750, 18249.99, 810.00, 360.00),
            (18250, 18749.99, 832.50, 370.00),
            (18750, 19249.99, 855.00, 380.00),
            (19250, 19749.99, 877.50, 390.00),
            (19750, 20249.99, 900.00, 400.00),
            (20250, 20749.99, 922.50, 410.00),
            (20750, 21249.99, 945.00, 420.00),
            (21250, 21749.99, 967.50, 430.00),
            (21750, 22249.99, 990.00, 440.00),
            (22250, 22749.99, 1012.50, 450.00),
            (22750, 23249.99, 1035.00, 460.00),
            (23250, 23749.99, 1057.50, 470.00),
            (23750, 24249.99, 1080.00, 480.00),
            (24250, 24749.99, 1102.50, 490.00),
            (24750, 29749.99, 1125.00, 500.00),
            (29750, float('inf'), 1125.00, 500.00),  # Maximum contribution
        ]
    }
    
    # PhilHealth rates (4% of monthly salary, split equally)
    PHILHEALTH_RATE = 0.04  # 4% total
    PHILHEALTH_MAX_SALARY = 80000.00  # Maximum salary base
    PHILHEALTH_MIN_CONTRIBUTION = 400.00  # Minimum total contribution
    
    # Pag-IBIG rates
    PAGIBIG_EMPLOYEE_RATE = 0.02  # 2% employee share
    PAGIBIG_EMPLOYER_RATE = 0.02  # 2% employer share
    PAGIBIG_MAX_EMPLOYEE = 100.00  # Maximum employee contribution
    PAGIBIG_MAX_EMPLOYER = 100.00  # Maximum employer contribution
    PAGIBIG_SALARY_CAP = 5000.00  # Salary cap for calculation

class AttendanceStatus(str, Enum):
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"
    UNDERTIME = "undertime"
    HALF_DAY = "half_day"
    ON_LEAVE = "on_leave"

class LeaveType(str, Enum):
    SICK_LEAVE = "sick_leave"
    VACATION_LEAVE = "vacation_leave"
    EMERGENCY_LEAVE = "emergency_leave"
    MATERNITY_LEAVE = "maternity_leave"
    PATERNITY_LEAVE = "paternity_leave"
    UNPAID_LEAVE = "unpaid_leave"

class LeaveStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class HolidayType(str, Enum):
    REGULAR_HOLIDAY = "regular_holiday"  # 200% pay
    SPECIAL_HOLIDAY = "special_holiday"  # 130% pay

# Philippine Labor Law Rates
class AttendanceDeductionRates:
    """Deduction rates based on Philippine labor practices"""
    
    # Late deductions (per minute or hour)
    LATE_GRACE_PERIOD_MINUTES = 10  # No deduction for first 10 minutes
    LATE_DEDUCTION_PER_MINUTE = True  # Deduct per minute after grace period
    
    # Absent deduction
    ABSENT_FULL_DAY_DEDUCTION = 1.0  # 100% of daily rate
    
    # Undertime deduction
    UNDERTIME_DEDUCTION_PER_MINUTE = True  # Deduct per minute
    
    # Half-day threshold
    HALF_DAY_HOURS = 4  # Less than 4 hours = half day

# Holiday Pay Rates (Philippine Labor Code)
class HolidayPayRates:
    """
    Based on Philippine Labor Code:
    - Regular Holiday (not worked): 100% pay
    - Regular Holiday (worked): 200% pay (100% + 100% premium)
    - Special Holiday (not worked): 0% pay (no work, no pay)
    - Special Holiday (worked): 130% pay (100% + 30% premium)
    """
    
    REGULAR_HOLIDAY_NOT_WORKED = 1.0  # 100%
    REGULAR_HOLIDAY_WORKED = 2.0  # 200%
    SPECIAL_HOLIDAY_NOT_WORKED = 0.0  # 0% (no work, no pay)
    SPECIAL_HOLIDAY_WORKED = 1.3  # 130%
    
    # Overtime on holidays
    REGULAR_HOLIDAY_OT_RATE = 2.6  # 200% + 30% OT
    SPECIAL_HOLIDAY_OT_RATE = 1.69  # 130% + 30% OT

# Leave Credits (Philippine Labor Code)
class LeaveCredits:
    """Standard leave credits per year"""
    
    SICK_LEAVE_ANNUAL = 15  # 15 days/year
    VACATION_LEAVE_ANNUAL = 15  # 15 days/year
    MATERNITY_LEAVE = 105  # 105 days (expanded maternity leave)
    PATERNITY_LEAVE = 7  # 7 days
    
    # Accumulation rules
    MAX_ACCUMULATED_SICK_LEAVE = 30
    MAX_ACCUMULATED_VACATION_LEAVE = 30