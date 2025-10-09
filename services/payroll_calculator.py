from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from typing import Dict, Any
from models.employee import EmployeeDB
from models.attendance import AttendanceDB
from utils.constants import SalaryType, AttendanceStatus
from services.benefits_calculator import BenefitsCalculator
from services.holiday_calculator import HolidayCalculator
from services.tax_calculator import TaxCalculator

class PayrollCalculator:
    """Calculate payroll for employees with all deductions and premiums"""
    
    @staticmethod
    def calculate_work_hours(time_in: str, time_out: str) -> float:
        """Calculate hours worked from time strings (HH:MM format)"""
        try:
            time_in_obj = datetime.strptime(time_in, "%H:%M")
            time_out_obj = datetime.strptime(time_out, "%H:%M")
            
            if time_out_obj < time_in_obj:
                time_out_obj += timedelta(days=1)
            
            duration = time_out_obj - time_in_obj
            return duration.total_seconds() / 3600
        except:
            return 0.0
    
    @staticmethod
    def convert_to_monthly_salary(employee: EmployeeDB, work_days: int, work_hours: float) -> float:
        """Convert salary to monthly equivalent for benefits calculation"""
        if employee.salary_type == SalaryType.MONTHLY:
            return employee.salary_rate
        elif employee.salary_type == SalaryType.DAILY:
            # Assume 22 working days per month
            return employee.salary_rate * 22
        elif employee.salary_type == SalaryType.HOURLY:
            # Assume 8 hours/day, 22 days/month
            return employee.salary_rate * 8 * 22
        return 0.0
    
    @staticmethod
    def calculate_prorated_allowances(
        employee: EmployeeDB,
        work_days: int,
        total_period_days: int,
        status_counts: dict
    ) -> Dict[str, float]:
        """
        Calculate prorated allowances based on attendance
        Returns dict with allowance breakdown
        """
        if not employee.allowances:
            return {}
        
        prorated_allowances = {}
        
        # If employee worked all days, give full allowances
        if status_counts['absent'] == 0:
            return employee.allowances.copy()
        
        # Prorate allowances based on work days
        # Formula: (work_days / total_period_days) * allowance_amount
        proration_factor = work_days / total_period_days if total_period_days > 0 else 0
        
        for allowance_name, amount in employee.allowances.items():
            prorated_allowances[allowance_name] = round(amount * proration_factor, 2)
        
        return prorated_allowances
    
    @staticmethod
    def calculate_for_employee(
        db: Session, 
        employee_id: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Calculate complete payroll for a single employee including all deductions and premiums"""
        
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
        if not employee:
            return None
        
        # Get attendance records
        attendance_records = db.query(AttendanceDB).filter(
            AttendanceDB.employee_id == employee_id,
            AttendanceDB.date >= start_date,
            AttendanceDB.date <= end_date
        ).all()
        
        # Calculate hourly and daily rates
        if employee.salary_type == SalaryType.HOURLY:
            hourly_rate = employee.salary_rate
            daily_rate = hourly_rate * 8
        elif employee.salary_type == SalaryType.DAILY:
            daily_rate = employee.salary_rate
            hourly_rate = daily_rate / 8
        else:  # MONTHLY
            daily_rate = employee.salary_rate / 30
            hourly_rate = daily_rate / 8
        
        # Initialize totals
        total_regular_hours = 0.0
        total_overtime_hours = 0.0
        total_nightshift_hours = 0.0
        total_work_days = 0
        
        # Deductions tracking
        total_late_deduction = 0.0
        total_absent_deduction = 0.0
        total_undertime_deduction = 0.0
        
        # Holiday tracking
        holiday_premium_pay = 0.0
        holiday_overtime_pay = 0.0
        
        # Status counts (for reporting)
        status_counts = {
            'present': 0,
            'late': 0,
            'absent': 0,
            'undertime': 0,
            'half_day': 0,
            'on_leave': 0
        }
        
        for record in attendance_records:
            # Track status
            status_key = record.status.value if hasattr(record.status, 'value') else str(record.status)
            if status_key in status_counts:
                status_counts[status_key] += 1
            
            # Skip if on leave (paid leave doesn't affect regular pay)
            if record.status == AttendanceStatus.ON_LEAVE:
                total_work_days += 1  # Count as worked for paid leave
                continue
            
            # Track deductions
            total_late_deduction += record.late_deduction or 0
            total_absent_deduction += record.absent_deduction or 0
            total_undertime_deduction += record.undertime_deduction or 0
            
            # If absent, skip work hours calculation
            if record.status == AttendanceStatus.ABSENT:
                continue
            
            # Calculate work hours
            if record.time_in and record.time_out:
                work_hours = PayrollCalculator.calculate_work_hours(record.time_in, record.time_out)
                
                # Check if it's a holiday
                if record.is_holiday and record.holiday_id:
                    # Get holiday details
                    from models.holidays import HolidayDB
                    holiday = db.query(HolidayDB).filter(HolidayDB.id == record.holiday_id).first()
                    
                    if holiday:
                        # Calculate holiday pay
                        holiday_calc = HolidayCalculator.calculate_holiday_pay(
                            daily_rate=daily_rate,
                            holiday_type=holiday.holiday_type,
                            worked=True,
                            hours_worked=work_hours,
                            overtime_hours=record.overtime_hours
                        )
                        
                        holiday_premium_pay += holiday_calc['base_pay']
                        holiday_overtime_pay += holiday_calc['overtime_pay']
                else:
                    # Regular day
                    total_regular_hours += work_hours
                    total_work_days += 1
            
            total_overtime_hours += record.overtime_hours or 0
            total_nightshift_hours += record.nightshift_hours or 0
        
        # Calculate base pay
        base_pay = 0.0
        if employee.salary_type == SalaryType.HOURLY:
            base_pay = total_regular_hours * hourly_rate
        elif employee.salary_type == SalaryType.DAILY:
            base_pay = total_work_days * daily_rate
        elif employee.salary_type == SalaryType.MONTHLY:
            period_days = (end_date - start_date).days + 1
            base_pay = (employee.salary_rate / 30) * period_days
        
        # Calculate additional pays (non-holiday)
        overtime_pay = total_overtime_hours * (employee.overtime_rate or (hourly_rate * 1.25))
        nightshift_pay = total_nightshift_hours * (employee.nightshift_rate or (hourly_rate * 1.10))
        
        # Calculate prorated allowances based on attendance
        total_period_days = (end_date - start_date).days + 1
        prorated_allowances = PayrollCalculator.calculate_prorated_allowances(
            employee, total_work_days, total_period_days, status_counts
        )
        allowances_total = sum(prorated_allowances.values())
        
        # Calculate monthly equivalent for benefits
        monthly_salary = PayrollCalculator.convert_to_monthly_salary(
            employee, total_work_days, total_regular_hours
        )
        
        # Calculate mandatory contributions
        contributions = BenefitsCalculator.calculate_all_contributions(monthly_salary)
        
        # Build deductions dictionary
        deductions = {
            'sss': contributions['sss']['employee'],
            'philhealth': contributions['philhealth']['employee'],
            'pagibig': contributions['pagibig']['employee'],
            'late': total_late_deduction,
            'absent': total_absent_deduction,
            'undertime': total_undertime_deduction
        }

        tax_info = TaxCalculator.calculate_tax_for_payroll(
            gross_pay=gross,
            mandatory_contributions=contributions,
            db=db
        )

        deductions['withholding_tax'] = tax_info['withholding_tax']        
        
        # Add custom taxes/deductions from employee record
        if employee.taxes:
            deductions.update(employee.taxes)
        
        # Calculate totals
        benefits_total = sum((employee.benefits or {}).values())
        deductions_total = sum(deductions.values())
        
        # Gross includes base pay, overtime, nightshift, holiday premiums, allowances, and benefits
        gross = (base_pay + overtime_pay + nightshift_pay + 
                holiday_premium_pay + holiday_overtime_pay + 
                allowances_total + benefits_total)
        
        # Net is gross minus all deductions
        net = round(gross - deductions_total, 2)
        
        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "base_pay": round(base_pay, 2),
            "overtime_pay": round(overtime_pay, 2),
            "nightshift_pay": round(nightshift_pay, 2),
            "holiday_premium_pay": round(holiday_premium_pay, 2),
            "holiday_overtime_pay": round(holiday_overtime_pay, 2),
            "allowances": prorated_allowances,
            "bonuses": None,
            "benefits": employee.benefits,
            "tax_calculation": tax_info,
            "deductions": deductions,
            "gross": round(gross, 2),
            "net": net,
            "mandatory_contributions": contributions,
            "monthly_salary_equivalent": round(monthly_salary, 2),
            "allowances_summary": {
                "configured_allowances": employee.allowances or {},
                "prorated_allowances": prorated_allowances,
                "total_allowances": round(allowances_total, 2),
                "proration_applied": status_counts['absent'] > 0
            },
            "attendance_summary": {
                "total_days": len(attendance_records),
                "work_days": total_work_days,
                "regular_hours": round(total_regular_hours, 2),
                "overtime_hours": round(total_overtime_hours, 2),
                "nightshift_hours": round(total_nightshift_hours, 2),
                "status_breakdown": status_counts,
                "deductions_breakdown": {
                    "late": round(total_late_deduction, 2),
                    "absent": round(total_absent_deduction, 2),
                    "undertime": round(total_undertime_deduction, 2),
                    "total": round(total_late_deduction + total_absent_deduction + total_undertime_deduction, 2)
                }
            }
        }