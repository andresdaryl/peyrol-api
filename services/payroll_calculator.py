from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from typing import Dict, Any
from models.employee import EmployeeDB
from models.attendance import AttendanceDB
from utils.constants import SalaryType
from services.benefits_calculator import BenefitsCalculator

class PayrollCalculator:
    """Calculate payroll for employees"""
    
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
    def calculate_for_employee(
        db: Session, 
        employee_id: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, Any]:
        """Calculate complete payroll for a single employee"""
        
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
        if not employee:
            return None
        
        # Get attendance records
        attendance_records = db.query(AttendanceDB).filter(
            AttendanceDB.employee_id == employee_id,
            AttendanceDB.date >= start_date,
            AttendanceDB.date <= end_date
        ).all()
        
        # Calculate totals
        total_work_hours = 0.0
        total_overtime_hours = 0.0
        total_nightshift_hours = 0.0
        total_work_days = len(attendance_records)
        
        for record in attendance_records:
            work_hours = PayrollCalculator.calculate_work_hours(record.time_in, record.time_out)
            total_work_hours += work_hours
            total_overtime_hours += record.overtime_hours
            total_nightshift_hours += record.nightshift_hours
        
        # Calculate base pay
        base_pay = 0.0
        if employee.salary_type == SalaryType.HOURLY:
            base_pay = total_work_hours * employee.salary_rate
        elif employee.salary_type == SalaryType.DAILY:
            base_pay = total_work_days * employee.salary_rate
        elif employee.salary_type == SalaryType.MONTHLY:
            period_days = (end_date - start_date).days + 1
            base_pay = (employee.salary_rate / 30) * period_days
        
        # Calculate additional pays
        overtime_pay = total_overtime_hours * (employee.overtime_rate or 0)
        nightshift_pay = total_nightshift_hours * (employee.nightshift_rate or 0)
        
        # Calculate monthly equivalent for benefits
        monthly_salary = PayrollCalculator.convert_to_monthly_salary(
            employee, total_work_days, total_work_hours
        )
        
        # Calculate mandatory contributions
        contributions = BenefitsCalculator.calculate_all_contributions(monthly_salary)
        
        # Build deductions dictionary
        deductions = {
            'sss': contributions['sss']['employee'],
            'philhealth': contributions['philhealth']['employee'],
            'pagibig': contributions['pagibig']['employee']
        }
        
        # Add custom taxes/deductions from employee record
        if employee.taxes:
            deductions.update(employee.taxes)
        
        # Calculate totals
        benefits_total = sum((employee.benefits or {}).values())
        deductions_total = sum(deductions.values())
        
        gross = base_pay + overtime_pay + nightshift_pay + benefits_total
        net = round(gross - deductions_total, 2)
        
        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "base_pay": round(base_pay, 2),
            "overtime_pay": round(overtime_pay, 2),
            "nightshift_pay": round(nightshift_pay, 2),
            "bonuses": None,
            "benefits": employee.benefits,
            "deductions": deductions,
            "gross": round(gross, 2),
            "net": net,
            "mandatory_contributions": contributions,
            "monthly_salary_equivalent": round(monthly_salary, 2)
        }