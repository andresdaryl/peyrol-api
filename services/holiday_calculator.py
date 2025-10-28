from datetime import date
from sqlalchemy.orm import Session
from models.holidays import HolidayDB
from utils.constants import HolidayType, HolidayPayRates

class HolidayCalculator:
    """Calculate holiday pay based on Philippine Labor Code"""
    
    @staticmethod
    def is_holiday(db: Session, check_date: date) -> tuple[bool, str, HolidayType]:
        """Check if a date is a holiday"""
        holiday = db.query(HolidayDB).filter(HolidayDB.date == check_date).first()
        if holiday:
            return True, holiday.id, holiday.holiday_type
        return False, None, None
    
    @staticmethod
    def calculate_holiday_pay(
        daily_rate: float,
        holiday_type: HolidayType,
        worked: bool,
        hours_worked: float = 0,
        overtime_hours: float = 0
    ) -> dict:
        """
        Calculate holiday pay based on type and whether employee worked
        
        Returns:
            dict with base_pay, overtime_pay, total
        """
        
        if holiday_type == HolidayType.REGULAR_HOLIDAY:
            if worked:
                # Worked on regular holiday: 200% of daily rate
                base_pay = daily_rate * HolidayPayRates.REGULAR_HOLIDAY_WORKED
                # Overtime on regular holiday: 260% (200% + 30% OT)
                hourly_rate = daily_rate / 8
                overtime_pay = overtime_hours * hourly_rate * HolidayPayRates.REGULAR_HOLIDAY_OT_RATE
            else:
                # Did not work on regular holiday: 100% pay (paid holiday)
                base_pay = daily_rate * HolidayPayRates.REGULAR_HOLIDAY_NOT_WORKED
                overtime_pay = 0
        
        else:  # SPECIAL_HOLIDAY
            if worked:
                # Worked on special holiday: 130% of daily rate
                base_pay = daily_rate * HolidayPayRates.SPECIAL_HOLIDAY_WORKED
                # Overtime on special holiday: 169% (130% + 30% OT)
                hourly_rate = daily_rate / 8
                overtime_pay = overtime_hours * hourly_rate * HolidayPayRates.SPECIAL_HOLIDAY_OT_RATE
            else:
                # Did not work on special holiday: no pay (no work, no pay)
                base_pay = 0
                overtime_pay = 0
        
        return {
            'base_pay': round(base_pay, 2),
            'overtime_pay': round(overtime_pay, 2),
            'total': round(base_pay + overtime_pay, 2),
            'rate_applied': HolidayPayRates.REGULAR_HOLIDAY_WORKED if worked and holiday_type == HolidayType.REGULAR_HOLIDAY 
                           else HolidayPayRates.SPECIAL_HOLIDAY_WORKED if worked 
                           else HolidayPayRates.REGULAR_HOLIDAY_NOT_WORKED if holiday_type == HolidayType.REGULAR_HOLIDAY
                           else 0
        }