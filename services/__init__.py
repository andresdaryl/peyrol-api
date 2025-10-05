"""
Services package - contains business logic and calculations
"""
from services.auth import AuthService
from services.payroll_calculator import PayrollCalculator
from services.benefits_calculator import BenefitsCalculator
from services.pdf_generator import PDFGenerator
from services.attendance_calculator import AttendanceCalculator
from services.holiday_calculator import HolidayCalculator
from services.leave_calculator import LeaveCalculator

__all__ = [
    'AuthService',
    'PayrollCalculator',
    'BenefitsCalculator',
    'PDFGenerator',
    'AttendanceCalculator',
    'HolidayCalculator',
    'LeaveCalculator'
]