from datetime import datetime, timedelta, time
from utils.constants import AttendanceDeductionRates, AttendanceStatus

class AttendanceCalculator:
    """Calculate attendance-related deductions and status"""
    
    @staticmethod
    def calculate_late_minutes(time_in: str, expected_time_in: str = "08:00") -> float:
        """Calculate how many minutes late an employee is"""
        try:
            actual = datetime.strptime(time_in, "%H:%M")
            expected = datetime.strptime(expected_time_in, "%H:%M")
            
            if actual <= expected:
                return 0.0
            
            difference = actual - expected
            minutes_late = difference.total_seconds() / 60
            
            # Apply grace period
            if minutes_late <= AttendanceDeductionRates.LATE_GRACE_PERIOD_MINUTES:
                return 0.0
            
            return minutes_late - AttendanceDeductionRates.LATE_GRACE_PERIOD_MINUTES
        except:
            return 0.0
    
    @staticmethod
    def calculate_undertime_minutes(time_out: str, expected_time_out: str = "17:00") -> float:
        """Calculate undertime minutes"""
        try:
            actual = datetime.strptime(time_out, "%H:%M")
            expected = datetime.strptime(expected_time_out, "%H:%M")
            
            if actual >= expected:
                return 0.0
            
            difference = expected - actual
            return difference.total_seconds() / 60
        except:
            return 0.0
    
    @staticmethod
    def calculate_late_deduction(late_minutes: float, hourly_rate: float) -> float:
        """Calculate monetary deduction for being late"""
        if late_minutes <= 0:
            return 0.0
        
        # Convert minutes to hours and multiply by hourly rate
        hours = late_minutes / 60
        return round(hours * hourly_rate, 2)
    
    @staticmethod
    def calculate_undertime_deduction(undertime_minutes: float, hourly_rate: float) -> float:
        """Calculate monetary deduction for undertime"""
        if undertime_minutes <= 0:
            return 0.0
        
        hours = undertime_minutes / 60
        return round(hours * hourly_rate, 2)
    
    @staticmethod
    def calculate_absent_deduction(daily_rate: float) -> float:
        """Calculate deduction for full day absence"""
        return round(daily_rate * AttendanceDeductionRates.ABSENT_FULL_DAY_DEDUCTION, 2)
    
    @staticmethod
    def determine_status(
        time_in: str = None,
        time_out: str = None,
        late_minutes: float = 0,
        undertime_minutes: float = 0,
        hours_worked: float = 0
    ) -> AttendanceStatus:
        """Determine attendance status based on time and hours"""
        
        if not time_in:
            return AttendanceStatus.ABSENT
        
        if hours_worked < AttendanceDeductionRates.HALF_DAY_HOURS:
            return AttendanceStatus.HALF_DAY
        
        if undertime_minutes > 0:
            return AttendanceStatus.UNDERTIME
        
        if late_minutes > 0:
            return AttendanceStatus.LATE
        
        return AttendanceStatus.PRESENT