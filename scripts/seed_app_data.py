#!/usr/bin/env python3
"""
Database Seeder Script for HRIS Application

Usage:
    python scripts/seed_app_data.py
    python scripts/seed_app_data.py --seed 42  # Use fixed random seed

This script populates the database with realistic mock data for testing.
It's idempotent - safe to run multiple times (skips existing special records).

Seeds:
- 1 SuperAdmin, 2 Admins
- ~8 Employees (various departments, salary types)
- ~10 Attendance records per employee
- 1-2 Leave requests per some employees
- 1 Leave balance per employee
- 3-5 Holidays
- 1 Payroll run with entries, payslips, and mandatory contributions
- Company profile (if missing)
- Tax/Benefits configs (if missing)
"""

import sys
import os
import argparse
from datetime import datetime, date, timedelta
from typing import List, Optional
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from sqlalchemy import select

# Import database session and models
from database import SessionLocal, engine
from models.user import UserDB, UserRole
from models.employee import EmployeeDB, SalaryType, EmployeeStatus
from models.attendance import AttendanceDB, ShiftType, AttendanceStatus
from models.leaves import LeaveDB, LeaveType, LeaveStatus, LeaveBalanceDB
from models.company import CompanyProfileDB
from models.holidays import HolidayDB, HolidayType
from models.benefits import BenefitsConfigDB, MandatoryContributionsDB
from models.taxes import TaxConfigDB
from models.payroll import PayrollRunDB, PayrollRunType, PayrollRunStatus
from models.payroll import PayrollEntryDB, PayslipDB

# Password hashing
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_users(db: Session) -> List[UserDB]:
    """Create admin users if they don't exist."""
    users = []
    
    # Check if SuperAdmin exists
    superadmin = db.execute(
        select(UserDB).where(UserDB.role == UserRole.SUPERADMIN)
    ).scalar_one_or_none()
    
    if not superadmin:
        superadmin = UserDB(
            email="superadmin@company.com",
            name="Super Administrator",
            role=UserRole.SUPERADMIN,
            hashed_password=hash_password("superadmin123"),
            is_active=True
        )
        db.add(superadmin)
        users.append(superadmin)
        print("✓ Created SuperAdmin")
    else:
        print("⊗ SuperAdmin already exists, skipping")
        users.append(superadmin)
    
    # Create admins if they don't exist
    admin_emails = ["admin1@company.com", "admin2@company.com"]
    admin_names = ["Admin One", "Admin Two"]
    
    for email, name in zip(admin_emails, admin_names):
        existing = db.execute(select(UserDB).where(UserDB.email == email)).scalar_one_or_none()
        if not existing:
            admin = UserDB(
                email=email,
                name=name,
                role=UserRole.ADMIN,
                hashed_password=hash_password("admin123"),
                is_active=True
            )
            db.add(admin)
            users.append(admin)
            print(f"✓ Created Admin: {name}")
        else:
            print(f"⊗ Admin {name} already exists, skipping")
            users.append(existing)
    
    db.flush()
    return users


def create_employees(db: Session) -> List[EmployeeDB]:
    """Create diverse employee records."""
    employees_data = [
        {
            "name": "Juan Dela Cruz",
            "email": "juan.delacruz@company.com",
            "contact": "+63 917 123 4567",
            "date_of_birth": date(1990, 5, 15),
            "hire_date": date(2020, 1, 10),
            "role": "Software Engineer",
            "department": "Engineering",
            "salary_type": SalaryType.MONTHLY,
            "salary_rate": 45000.0,
            "allowances": {"transportation": 2000, "meal": 1500},
            "benefits": {"hmo": True, "rice_subsidy": 1500},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.10,
        },
        {
            "name": "Maria Santos",
            "email": "maria.santos@company.com",
            "contact": "+63 918 234 5678",
            "date_of_birth": date(1988, 8, 22),
            "hire_date": date(2019, 3, 15),
            "role": "HR Manager",
            "department": "Human Resources",
            "salary_type": SalaryType.MONTHLY,
            "salary_rate": 55000.0,
            "allowances": {"transportation": 2500, "meal": 2000},
            "benefits": {"hmo": True, "rice_subsidy": 1500},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.10,
        },
        {
            "name": "Pedro Reyes",
            "email": "pedro.reyes@company.com",
            "contact": "+63 919 345 6789",
            "date_of_birth": date(1992, 3, 10),
            "hire_date": date(2021, 6, 1),
            "role": "Accountant",
            "department": "Finance",
            "salary_type": SalaryType.MONTHLY,
            "salary_rate": 40000.0,
            "allowances": {"transportation": 1800, "meal": 1500},
            "benefits": {"hmo": True, "rice_subsidy": 1500},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.10,
        },
        {
            "name": "Ana Gonzales",
            "email": "ana.gonzales@company.com",
            "contact": "+63 920 456 7890",
            "date_of_birth": date(1995, 11, 5),
            "hire_date": date(2022, 2, 14),
            "role": "Marketing Specialist",
            "department": "Marketing",
            "salary_type": SalaryType.MONTHLY,
            "salary_rate": 38000.0,
            "allowances": {"transportation": 1500, "meal": 1200},
            "benefits": {"hmo": True, "rice_subsidy": 1500},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.10,
        },
        {
            "name": "Jose Rizal",
            "email": "jose.rizal@company.com",
            "contact": "+63 921 567 8901",
            "date_of_birth": date(1993, 6, 19),
            "hire_date": date(2020, 9, 1),
            "role": "Project Manager",
            "department": "Engineering",
            "salary_type": SalaryType.MONTHLY,
            "salary_rate": 60000.0,
            "allowances": {"transportation": 3000, "meal": 2500},
            "benefits": {"hmo": True, "rice_subsidy": 1500, "car_allowance": 5000},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.10,
        },
        {
            "name": "Carmen Torres",
            "email": "carmen.torres@company.com",
            "contact": "+63 922 678 9012",
            "date_of_birth": date(1991, 9, 25),
            "hire_date": date(2021, 1, 20),
            "role": "Designer",
            "department": "Creative",
            "salary_type": SalaryType.MONTHLY,
            "salary_rate": 42000.0,
            "allowances": {"transportation": 2000, "meal": 1500},
            "benefits": {"hmo": True, "rice_subsidy": 1500},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.10,
        },
        {
            "name": "Roberto Diaz",
            "email": "roberto.diaz@company.com",
            "contact": "+63 923 789 0123",
            "date_of_birth": date(1989, 12, 8),
            "hire_date": date(2018, 5, 10),
            "role": "Senior Developer",
            "department": "Engineering",
            "salary_type": SalaryType.MONTHLY,
            "salary_rate": 65000.0,
            "allowances": {"transportation": 3000, "meal": 2500},
            "benefits": {"hmo": True, "rice_subsidy": 1500},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.10,
        },
        {
            "name": "Linda Cruz",
            "email": "linda.cruz@company.com",
            "contact": "+63 924 890 1234",
            "date_of_birth": date(1994, 4, 17),
            "hire_date": date(2022, 8, 1),
            "role": "Customer Support",
            "department": "Operations",
            "salary_type": SalaryType.DAILY,
            "salary_rate": 600.0,
            "allowances": {"transportation": 100, "meal": 100},
            "benefits": {"rice_subsidy": 1500},
            "taxes": {},
            "overtime_rate": 1.25,
            "nightshift_rate": 1.30,
        },
    ]
    
    employees = []
    for emp_data in employees_data:
        existing = db.execute(
            select(EmployeeDB).where(EmployeeDB.email == emp_data["email"])
        ).scalar_one_or_none()
        
        if not existing:
            employee = EmployeeDB(**emp_data)
            db.add(employee)
            employees.append(employee)
            print(f"✓ Created Employee: {emp_data['name']}")
        else:
            print(f"⊗ Employee {emp_data['name']} already exists, skipping")
            employees.append(existing)
    
    db.flush()
    return employees


def create_attendance_records(db: Session, employees: List[EmployeeDB]):
    """Create attendance records for the last ~10 working days."""
    today = date.today()
    
    for employee in employees:
        # Generate for last 14 days (mix of working days)
        for days_ago in range(14, 0, -1):
            record_date = today - timedelta(days=days_ago)
            
            # Skip weekends
            if record_date.weekday() >= 5:
                continue
            
            # Check if attendance already exists
            existing = db.execute(
                select(AttendanceDB).where(
                    AttendanceDB.employee_id == employee.id,
                    AttendanceDB.date == record_date
                )
            ).scalar_one_or_none()
            
            if existing:
                continue
            
            # Randomly determine attendance status
            status_roll = random.random()
            
            if status_roll < 0.75:  # 75% present
                status = AttendanceStatus.PRESENT
                regular_hours = 8.0
                overtime_hours = random.choice([0.0, 0.0, 0.0, 1.0, 2.0])
                late_minutes = random.choice([0.0, 0.0, 0.0, 15.0, 30.0])
                undertime_minutes = 0.0
                time_in = "08:00"
                time_out = "17:00"
            elif status_roll < 0.85:  # 10% late
                status = AttendanceStatus.LATE
                regular_hours = 7.5
                overtime_hours = 0.0
                late_minutes = random.choice([30.0, 45.0, 60.0])
                undertime_minutes = 0.0
                time_in = "09:00"
                time_out = "17:00"
            elif status_roll < 0.90:  # 5% undertime
                status = AttendanceStatus.UNDERTIME
                regular_hours = 6.0
                overtime_hours = 0.0
                late_minutes = 0.0
                undertime_minutes = 120.0
                time_in = "08:00"
                time_out = "15:00"
            else:  # 10% absent
                status = AttendanceStatus.ABSENT
                regular_hours = 0.0
                overtime_hours = 0.0
                late_minutes = 0.0
                undertime_minutes = 0.0
                time_in = None
                time_out = None
            
            # Simple deduction calculation (hourly rate based)
            hourly_rate = employee.salary_rate / 22 / 8 if employee.salary_type == SalaryType.MONTHLY else employee.salary_rate / 8
            late_deduction = (late_minutes / 60) * hourly_rate if status == AttendanceStatus.LATE else 0.0
            undertime_deduction = (undertime_minutes / 60) * hourly_rate if status == AttendanceStatus.UNDERTIME else 0.0
            absent_deduction = employee.salary_rate / 22 if status == AttendanceStatus.ABSENT and employee.salary_type == SalaryType.MONTHLY else employee.salary_rate if status == AttendanceStatus.ABSENT else 0.0
            
            attendance = AttendanceDB(
                employee_id=employee.id,
                date=record_date,
                time_in=time_in,
                time_out=time_out,
                shift_type=ShiftType.DAY,
                regular_hours=regular_hours,
                overtime_hours=overtime_hours,
                nightshift_hours=0.0,
                status=status,
                late_minutes=late_minutes,
                undertime_minutes=undertime_minutes,
                late_deduction=late_deduction,
                absent_deduction=absent_deduction,
                undertime_deduction=undertime_deduction,
                is_holiday=False,
                holiday_id=None,
                notes=None
            )
            db.add(attendance)
    
    db.flush()
    print(f"✓ Created attendance records for {len(employees)} employees")


def create_leaves(db: Session, employees: List[EmployeeDB]):
    """Create leave requests for some employees."""
    leave_count = 0
    
    # Create 1-2 leaves for about half the employees
    for employee in random.sample(employees, k=min(5, len(employees))):
        num_leaves = random.randint(1, 2)
        
        for _ in range(num_leaves):
            leave_type = random.choice(list(LeaveType))
            start_date = date.today() - timedelta(days=random.randint(5, 30))
            days_count = random.randint(1, 5)
            end_date = start_date + timedelta(days=days_count - 1)
            status = random.choice([LeaveStatus.APPROVED, LeaveStatus.PENDING, LeaveStatus.APPROVED])
            
            leave = LeaveDB(
                employee_id=employee.id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                days_count=days_count,
                reason=f"Personal {leave_type.value} leave request",
                status=status,
                approved_by=None if status == LeaveStatus.PENDING else "admin1@company.com",
                approved_at=datetime.now() if status == LeaveStatus.APPROVED else None,
                rejection_reason=None,
                attachment_url=None
            )
            db.add(leave)
            leave_count += 1
    
    db.flush()
    print(f"✓ Created {leave_count} leave requests")


def create_leave_balances(db: Session, employees: List[EmployeeDB]):
    """Create leave balance records for all employees."""
    current_year = date.today().year
    
    for employee in employees:
        existing = db.execute(
            select(LeaveBalanceDB).where(
                LeaveBalanceDB.employee_id == employee.id,
                LeaveBalanceDB.year == current_year
            )
        ).scalar_one_or_none()
        
        if not existing:
            sick_used = random.uniform(0, 5)
            vacation_used = random.uniform(0, 7)
            
            balance = LeaveBalanceDB(
                employee_id=employee.id,
                sick_leave_balance=15.0,
                vacation_leave_balance=15.0,
                year=current_year,
                sick_leave_used=sick_used,
                vacation_leave_used=vacation_used
            )
            db.add(balance)
    
    db.flush()
    print(f"✓ Created leave balances for {len(employees)} employees")


def create_company_profile(db: Session):
    """Create company profile if it doesn't exist."""
    existing = db.execute(
        select(CompanyProfileDB).where(CompanyProfileDB.id == "company_001")
    ).scalar_one_or_none()
    
    if not existing:
        profile = CompanyProfileDB(
            id="company_001",
            company_name="TechCorp Philippines Inc.",
            address="123 Business Ave, Makati City, Metro Manila 1200",
            contact_number="+63 2 8123 4567",
            email="info@techcorp.ph",
            tax_id="123-456-789-000",
            logo_url=None
        )
        db.add(profile)
        db.flush()
        print("✓ Created company profile")
    else:
        print("⊗ Company profile already exists, skipping")


def create_holidays(db: Session):
    """Create holiday records."""
    current_year = date.today().year
    
    holidays_data = [
        {
            "name": "New Year's Day",
            "date": date(current_year, 1, 1),
            "holiday_type": HolidayType.REGULAR_HOLIDAY,
            "description": "Start of the new year",
            "is_recurring": True
        },
        {
            "name": "Labor Day",
            "date": date(current_year, 5, 1),
            "holiday_type": HolidayType.REGULAR_HOLIDAY,
            "description": "International Workers' Day",
            "is_recurring": True
        },
        {
            "name": "Independence Day",
            "date": date(current_year, 6, 12),
            "holiday_type": HolidayType.REGULAR_HOLIDAY,
            "description": "Philippine Independence Day",
            "is_recurring": True
        },
        {
            "name": "Bonifacio Day",
            "date": date(current_year, 11, 30),
            "holiday_type": HolidayType.REGULAR_HOLIDAY,
            "description": "National Heroes Day",
            "is_recurring": True
        },
        {
            "name": "Christmas Day",
            "date": date(current_year, 12, 25),
            "holiday_type": HolidayType.REGULAR_HOLIDAY,
            "description": "Christmas celebration",
            "is_recurring": True
        },
        {
            "name": "Rizal Day",
            "date": date(current_year, 12, 30),
            "holiday_type": HolidayType.REGULAR_HOLIDAY,
            "description": "Commemoration of Dr. Jose Rizal",
            "is_recurring": True
        },
    ]
    
    created_count = 0
    for holiday_data in holidays_data:
        existing = db.execute(
            select(HolidayDB).where(HolidayDB.date == holiday_data["date"])
        ).scalar_one_or_none()
        
        if not existing:
            holiday = HolidayDB(**holiday_data)
            db.add(holiday)
            created_count += 1
    
    db.flush()
    print(f"✓ Created {created_count} holidays")


def create_benefits_config(db: Session):
    """Create benefits configuration if missing."""
    current_year = str(date.today().year)
    
    configs = [
        {
            "benefit_type": "sss",
            "year": current_year,
            "config_data": {
                "employee_share": 0.045,
                "employer_share": 0.095,
                "min_salary": 4250,
                "max_salary": 30000
            },
            "notes": "SSS contribution rates for employees and employers"
        },
        {
            "benefit_type": "philhealth",
            "year": current_year,
            "config_data": {
                "premium_rate": 0.05,
                "employee_share": 0.025,
                "employer_share": 0.025,
                "max_salary": 100000
            },
            "notes": "PhilHealth contribution rates"
        },
        {
            "benefit_type": "pagibig",
            "year": current_year,
            "config_data": {
                "employee_rate_low": 0.01,
                "employee_rate_high": 0.02,
                "employer_rate": 0.02,
                "threshold": 1500
            },
            "notes": "Pag-IBIG contribution rates"
        }
    ]
    
    created_count = 0
    for config_data in configs:
        existing = db.execute(
            select(BenefitsConfigDB).where(
                BenefitsConfigDB.benefit_type == config_data["benefit_type"],
                BenefitsConfigDB.year == config_data["year"]
            )
        ).scalar_one_or_none()
        
        if not existing:
            config = BenefitsConfigDB(**config_data)
            db.add(config)
            created_count += 1
    
    db.flush()
    if created_count > 0:
        print(f"✓ Created {created_count} benefits configurations")
    else:
        print("⊗ Benefits configurations already exist, skipping")


def create_tax_config(db: Session):
    """Create tax configuration if missing."""
    current_year = str(date.today().year)
    
    existing = db.execute(
        select(TaxConfigDB).where(
            TaxConfigDB.tax_type == "withholding_tax",
            TaxConfigDB.year == current_year
        )
    ).scalar_one_or_none()
    
    if not existing:
        tax_config = TaxConfigDB(
            tax_type="withholding_tax",
            year=current_year,
            tax_brackets=[
                {"min": 0, "max": 20833, "rate": 0.00, "base": 0},
                {"min": 20833, "max": 33333, "rate": 0.15, "base": 0},
                {"min": 33333, "max": 66667, "rate": 0.20, "base": 1875},
                {"min": 66667, "max": 166667, "rate": 0.25, "base": 8541.80},
                {"min": 166667, "max": 666667, "rate": 0.30, "base": 33541.80},
                {"min": 666667, "max": 1e12, "rate": 0.35, "base": 183541.80}
            ],
            notes="Philippine withholding tax brackets"
        )
        db.add(tax_config)
        db.flush()
        print("✓ Created tax configuration")
    else:
        print("⊗ Tax configuration already exists, skipping")


def create_payroll_run(db: Session, employees: List[EmployeeDB]):
    """Create a payroll run with entries, payslips, and contributions."""
    # Create payroll run for last pay period (e.g., 16-30 of last month)
    today = date.today()
    
    # Determine last pay period
    if today.day <= 15:
        end_date = date(today.year, today.month, 15) - timedelta(days=15)
        start_date = date(end_date.year, end_date.month, 16)
    else:
        end_date = date(today.year, today.month, 15)
        start_date = date(end_date.year, end_date.month, 1)
    
    # Check if payroll run exists
    existing_run = db.execute(
        select(PayrollRunDB).where(
            PayrollRunDB.start_date == start_date,
            PayrollRunDB.end_date == end_date
        )
    ).scalar_one_or_none()
    
    if existing_run:
        print("⊗ Payroll run already exists for this period, skipping")
        return
    
    payroll_run = PayrollRunDB(
        start_date=start_date,
        end_date=end_date,
        type=PayrollRunType.BIWEEKLY,
        status=PayrollRunStatus.DRAFT
    )
    db.add(payroll_run)
    db.flush()
    
    print(f"✓ Created payroll run for {start_date} to {end_date}")
    
    # Create payroll entries for each employee
    for employee in employees:
        # Calculate base pay (half month for semi-monthly)
        if employee.salary_type == SalaryType.MONTHLY:
            base_pay = employee.salary_rate / 2
        else:  # DAILY
            base_pay = employee.salary_rate * 11  # Assume ~11 working days
        
        # Calculate overtime and night shift (simplified)
        overtime_pay = random.uniform(0, 2000)
        nightshift_pay = random.uniform(0, 1000)
        
        # Extract allowances
        allowances = employee.allowances or {}
        bonuses = {}
        
        # Calculate benefits deductions (simplified)
        monthly_salary = employee.salary_rate if employee.salary_type == SalaryType.MONTHLY else employee.salary_rate * 22
        
        sss_employee = min(monthly_salary * 0.045, 1350)  # Cap at 30k salary
        philhealth_employee = min(monthly_salary * 0.025, 2500)
        pagibig_employee = 100 if monthly_salary <= 1500 else min(monthly_salary * 0.02, 200)
        
        # Withholding tax (simplified - use basic bracket)
        taxable_income = base_pay + overtime_pay + nightshift_pay
        if taxable_income <= 20833:
            withholding_tax = 0
        elif taxable_income <= 33333:
            withholding_tax = (taxable_income - 20833) * 0.15
        else:
            withholding_tax = 1875 + (taxable_income - 33333) * 0.20
        
        benefits = {
            "sss": sss_employee,
            "philhealth": philhealth_employee,
            "pagibig": pagibig_employee
        }
        
        deductions = {
            "withholding_tax": round(withholding_tax, 2),
            "late_deduction": random.uniform(0, 500),
            "absent_deduction": random.uniform(0, 300)
        }
        
        total_allowances = sum(allowances.values())
        total_deductions = sum(deductions.values()) + sum(benefits.values())
        
        gross = base_pay + overtime_pay + nightshift_pay + total_allowances
        net = gross - total_deductions
        
        payroll_entry = PayrollEntryDB(
            payroll_run_id=payroll_run.id,
            employee_id=employee.id,
            employee_name=employee.name,
            base_pay=round(base_pay, 2),
            overtime_pay=round(overtime_pay, 2),
            nightshift_pay=round(nightshift_pay, 2),
            allowances=allowances,
            bonuses=bonuses,
            benefits=benefits,
            deductions=deductions,
            gross=round(gross, 2),
            net=round(net, 2),
            is_finalized=False,
            version=1,
            edit_history=[]
        )
        db.add(payroll_entry)
        db.flush()
        
        # Create payslip
        payslip = PayslipDB(
            payroll_entry_id=payroll_entry.id,
            employee_id=employee.id,
            pdf_base64=None,  # Leave empty or add placeholder
            is_editable=True,
            version=1
        )
        db.add(payslip)
        
        # Create mandatory contributions
        contributions = MandatoryContributionsDB(
            employee_id=employee.id,
            payroll_entry_id=payroll_entry.id,
            sss_employee=round(sss_employee, 2),
            sss_employer=round(sss_employee * 2.11, 2),  # Employer share is ~2x
            philhealth_employee=round(philhealth_employee, 2),
            philhealth_employer=round(philhealth_employee, 2),
            pagibig_employee=round(pagibig_employee, 2),
            pagibig_employer=round(pagibig_employee, 2),
            total_employee_contribution=round(sss_employee + philhealth_employee + pagibig_employee, 2),
            calculation_details={
                "base_salary": monthly_salary,
                "computed_at": datetime.now().isoformat()
            }
        )
        db.add(contributions)
    
    db.flush()
    print(f"✓ Created payroll entries, payslips, and contributions for {len(employees)} employees")


# ============================================================================
# MAIN SEEDER FUNCTION
# ============================================================================

def seed_database(seed_value: Optional[int] = None):
    """Main seeding function."""
    if seed_value is not None:
        random.seed(seed_value)
        print(f"🎲 Using random seed: {seed_value}")
    
    print("\n" + "="*60)
    print("🌱 STARTING DATABASE SEEDER")
    print("="*60 + "\n")
    
    db = SessionLocal()
    
    try:
        # Seed in order (respecting foreign key dependencies)
        print("📋 Step 1: Creating users...")
        users = create_users(db)
        
        print("\n📋 Step 2: Creating employees...")
        employees = create_employees(db)
        
        print("\n📋 Step 3: Creating company profile...")
        create_company_profile(db)
        
        print("\n📋 Step 4: Creating holidays...")
        create_holidays(db)
        
        print("\n📋 Step 5: Creating benefits configuration...")
        create_benefits_config(db)
        
        print("\n📋 Step 6: Creating tax configuration...")
        create_tax_config(db)
        
        print("\n📋 Step 7: Creating attendance records...")
        create_attendance_records(db, employees)
        
        print("\n📋 Step 8: Creating leave requests...")
        create_leaves(db, employees)
        
        print("\n📋 Step 9: Creating leave balances...")
        create_leave_balances(db, employees)
        
        print("\n📋 Step 10: Creating payroll run with entries...")
        create_payroll_run(db, employees)
        
        # Commit all changes
        db.commit()
        
        print("\n" + "="*60)
        print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n📊 Summary:")
        print(f"   • Users: {len(users)} (1 SuperAdmin, 2 Admins)")
        print(f"   • Employees: {len(employees)}")
        print(f"   • Attendance records: ~{len(employees) * 10} (10 per employee)")
        print(f"   • Leave requests: Multiple")
        print(f"   • Leave balances: {len(employees)}")
        print(f"   • Holidays: 5")
        print(f"   • Payroll entries: {len(employees)}")
        print(f"   • Payslips: {len(employees)}")
        print(f"   • Contributions: {len(employees)}")
        print("\n🔑 Login credentials:")
        print("   SuperAdmin: superadmin@company.com / superadmin123")
        print("   Admin 1: admin1@company.com / admin123")
        print("   Admin 2: admin2@company.com / admin123")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("🔄 Rolling back transaction...")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the database with mock data")
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible data generation",
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        seed_database(seed_value=args.seed)
    except Exception as e:
        print(f"\n💥 Fatal error: {str(e)}")
        sys.exit(1)