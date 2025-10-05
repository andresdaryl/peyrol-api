from datetime import date, timedelta
from sqlalchemy.orm import Session
from models.leaves import LeaveDB, LeaveBalanceDB
from models.holidays import HolidayDB
from utils.constants import LeaveType, LeaveStatus, LeaveCredits

class LeaveCalculator:
    """Manage leave balances and calculations"""
    
    @staticmethod
    def calculate_working_days(start_date: date, end_date: date, db: Session) -> int:
        """Calculate working days excluding weekends and holidays"""
        working_days = 0
        current = start_date
        
        while current <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current.weekday() < 5:
                # Check if it's a holiday
                holiday = db.query(HolidayDB).filter(HolidayDB.date == current).first()
                if not holiday:
                    working_days += 1
            current += timedelta(days=1)
        
        return working_days
    
    @staticmethod
    def check_leave_balance(
        db: Session,
        employee_id: str,
        leave_type: LeaveType,
        days_requested: int
    ) -> tuple[bool, float]:
        """Check if employee has enough leave balance"""
        
        balance = db.query(LeaveBalanceDB).filter(
            LeaveBalanceDB.employee_id == employee_id
        ).first()
        
        if not balance:
            return False, 0
        
        if leave_type == LeaveType.SICK_LEAVE:
            available = balance.sick_leave_balance
        elif leave_type == LeaveType.VACATION_LEAVE:
            available = balance.vacation_leave_balance
        else:
            # Other leave types don't require balance check
            return True, 0
        
        return available >= days_requested, available
    
    @staticmethod
    def deduct_leave(
        db: Session,
        employee_id: str,
        leave_type: LeaveType,
        days: float
    ):
        """Deduct leave from employee balance"""
        
        balance = db.query(LeaveBalanceDB).filter(
            LeaveBalanceDB.employee_id == employee_id
        ).first()
        
        if not balance:
            return
        
        if leave_type == LeaveType.SICK_LEAVE:
            balance.sick_leave_balance -= days
            balance.sick_leave_used += days
        elif leave_type == LeaveType.VACATION_LEAVE:
            balance.vacation_leave_balance -= days
            balance.vacation_leave_used += days
        
        db.commit()
    
    @staticmethod
    def restore_leave(
        db: Session,
        employee_id: str,
        leave_type: LeaveType,
        days: float
    ):
        """Restore leave balance (when leave is cancelled/rejected)"""
        
        balance = db.query(LeaveBalanceDB).filter(
            LeaveBalanceDB.employee_id == employee_id
        ).first()
        
        if not balance:
            return
        
        if leave_type == LeaveType.SICK_LEAVE:
            balance.sick_leave_balance += days
            balance.sick_leave_used -= days
        elif leave_type == LeaveType.VACATION_LEAVE:
            balance.vacation_leave_balance += days
            balance.vacation_leave_used -= days
        
        db.commit()
    
    @staticmethod
    def reset_annual_leaves(db: Session, employee_id: str, year: int):
        """Reset leave balances for new year"""
        
        balance = db.query(LeaveBalanceDB).filter(
            LeaveBalanceDB.employee_id == employee_id
        ).first()
        
        if not balance:
            # Create new balance
            balance = LeaveBalanceDB(
                employee_id=employee_id,
                year=year,
                sick_leave_balance=LeaveCredits.SICK_LEAVE_ANNUAL,
                vacation_leave_balance=LeaveCredits.VACATION_LEAVE_ANNUAL
            )
            db.add(balance)
        else:
            # Reset for new year with carryover limits
            balance.year = year
            balance.sick_leave_balance = min(
                balance.sick_leave_balance + LeaveCredits.SICK_LEAVE_ANNUAL,
                LeaveCredits.MAX_ACCUMULATED_SICK_LEAVE
            )
            balance.vacation_leave_balance = min(
                balance.vacation_leave_balance + LeaveCredits.VACATION_LEAVE_ANNUAL,
                LeaveCredits.MAX_ACCUMULATED_VACATION_LEAVE
            )
            balance.sick_leave_used = 0
            balance.vacation_leave_used = 0
        
        db.commit()