from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta, date, timezone
from typing import Optional
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from models.employee import EmployeeDB
from models.attendance import AttendanceDB
from models.payroll import PayrollRunDB, PayrollEntryDB
from utils.constants import EmployeeStatus

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get overall dashboard statistics"""
    
    # Employee stats
    total_employees = db.query(EmployeeDB).count()
    active_employees = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE
    ).count()
    inactive_employees = total_employees - active_employees
    
    # New employees this month
    first_day_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_this_month = db.query(EmployeeDB).filter(
        EmployeeDB.created_at >= first_day_of_month
    ).count()
    
    # New employees last month
    first_day_last_month = (first_day_of_month - timedelta(days=1)).replace(day=1)
    new_last_month = db.query(EmployeeDB).filter(
        and_(
            EmployeeDB.created_at >= first_day_last_month,
            EmployeeDB.created_at < first_day_of_month
        )
    ).count()
    
    # Calculate change percentage
    if new_last_month > 0:
        employee_change = ((new_this_month - new_last_month) / new_last_month) * 100
    else:
        employee_change = 100.0 if new_this_month > 0 else 0.0
    
    # Attendance stats for today
    today = date.today()
    today_attendance = db.query(AttendanceDB).filter(
        AttendanceDB.date == today
    ).all()
    
    today_present = len(today_attendance)
    today_absent = active_employees - today_present
    today_late = sum(1 for att in today_attendance if att.time_in > "09:00")  # Assuming 9 AM is on-time
    today_on_leave = 0  # You can implement leave tracking separately
    
    today_rate = (today_present / active_employees * 100) if active_employees > 0 else 0
    
    # Yesterday's attendance rate
    yesterday = today - timedelta(days=1)
    yesterday_attendance = db.query(AttendanceDB).filter(
        AttendanceDB.date == yesterday
    ).count()
    yesterday_rate = (yesterday_attendance / active_employees * 100) if active_employees > 0 else 0
    
    # Payroll stats
    total_runs = db.query(PayrollRunDB).count()
    
    # This month's payroll
    this_month_runs = db.query(PayrollRunDB).filter(
        extract('year', PayrollRunDB.start_date) == datetime.now().year,
        extract('month', PayrollRunDB.start_date) == datetime.now().month
    ).all()
    
    this_month_amount = 0
    for run in this_month_runs:
        entries = db.query(PayrollEntryDB).filter(
            PayrollEntryDB.payroll_run_id == run.id
        ).all()
        this_month_amount += sum(entry.net for entry in entries)
    
    # Last month's payroll
    last_month = datetime.now().month - 1 if datetime.now().month > 1 else 12
    last_month_year = datetime.now().year if datetime.now().month > 1 else datetime.now().year - 1
    
    last_month_runs = db.query(PayrollRunDB).filter(
        extract('year', PayrollRunDB.start_date) == last_month_year,
        extract('month', PayrollRunDB.start_date) == last_month
    ).all()
    
    last_month_amount = 0
    for run in last_month_runs:
        entries = db.query(PayrollEntryDB).filter(
            PayrollEntryDB.payroll_run_id == run.id
        ).all()
        last_month_amount += sum(entry.net for entry in entries)
    
    # Average salary
    all_entries = db.query(PayrollEntryDB).all()
    average_salary = (sum(entry.net for entry in all_entries) / len(all_entries)) if all_entries else 0
    
    # Year to date total
    year_runs = db.query(PayrollRunDB).filter(
        extract('year', PayrollRunDB.start_date) == datetime.now().year
    ).all()
    
    total_ytd = 0
    for run in year_runs:
        entries = db.query(PayrollEntryDB).filter(
            PayrollEntryDB.payroll_run_id == run.id
        ).all()
        total_ytd += sum(entry.net for entry in entries)
    
    return {
        "employees": {
            "total": total_employees,
            "active": active_employees,
            "inactive": inactive_employees,
            "newThisMonth": new_this_month,
            "changeFromLastMonth": round(employee_change, 1)
        },
        "attendance": {
            "todayPresent": today_present,
            "todayAbsent": today_absent,
            "todayLate": today_late,
            "todayOnLeave": today_on_leave,
            "todayRate": round(today_rate, 1),
            "yesterdayRate": round(yesterday_rate, 1)
        },
        "payroll": {
            "totalRuns": total_runs,
            "thisMonthAmount": round(this_month_amount, 2),
            "lastMonthAmount": round(last_month_amount, 2),
            "averageSalary": round(average_salary, 2),
            "totalYearToDate": round(total_ytd, 2)
        }
    }


@router.get("/attendance-trends")
async def get_attendance_trends(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance trends for the last N days"""
    
    labels = []
    present = []
    absent = []
    late = []
    rates = []
    
    total_active = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE
    ).count()
    
    for i in range(days - 1, -1, -1):
        target_date = date.today() - timedelta(days=i)
        labels.append(target_date.isoformat())
        
        # Get attendance for this date
        attendance_records = db.query(AttendanceDB).filter(
            AttendanceDB.date == target_date
        ).all()
        
        present_count = len(attendance_records)
        absent_count = total_active - present_count
        late_count = sum(1 for att in attendance_records if att.time_in > "09:00")
        rate = (present_count / total_active * 100) if total_active > 0 else 0
        
        present.append(present_count)
        absent.append(absent_count)
        late.append(late_count)
        rates.append(round(rate, 1))
    
    return {
        "labels": labels,
        "present": present,
        "absent": absent,
        "late": late,
        "rates": rates
    }


@router.get("/attendance-breakdown")
async def get_attendance_breakdown(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get today's attendance breakdown"""
    
    today = date.today()
    total_active = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE
    ).count()
    
    attendance_records = db.query(AttendanceDB).filter(
        AttendanceDB.date == today
    ).all()
    
    present = len(attendance_records)
    absent = total_active - present
    late = sum(1 for att in attendance_records if att.time_in > "09:00")
    on_leave = 0  # Implement leave tracking separately
    
    return {
        "present": present,
        "absent": absent,
        "late": late,
        "onLeave": on_leave
    }


@router.get("/payroll-trends")
async def get_payroll_trends(
    months: int = 6,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payroll trends for the last N months"""
    
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    labels = []
    amounts = []
    employee_counts = []
    
    for i in range(months - 1, -1, -1):
        target_date = datetime.now() - timedelta(days=i * 30)
        month = target_date.month
        year = target_date.year
        
        labels.append(f"{month_names[month - 1]} {year}")
        
        # Get payroll runs for this month
        month_runs = db.query(PayrollRunDB).filter(
            extract('year', PayrollRunDB.start_date) == year,
            extract('month', PayrollRunDB.start_date) == month
        ).all()
        
        month_total = 0
        unique_employees = set()
        
        for run in month_runs:
            entries = db.query(PayrollEntryDB).filter(
                PayrollEntryDB.payroll_run_id == run.id
            ).all()
            month_total += sum(entry.net for entry in entries)
            unique_employees.update(entry.employee_id for entry in entries)
        
        amounts.append(round(month_total, 2))
        employee_counts.append(len(unique_employees))
    
    return {
        "labels": labels,
        "amounts": amounts,
        "employeeCounts": employee_counts
    }


@router.get("/employees-by-department")
async def get_employees_by_department(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get employee count grouped by department"""
    
    results = db.query(
        EmployeeDB.department,
        func.count(EmployeeDB.id).label('count')
    ).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE,
        EmployeeDB.department.isnot(None)
    ).group_by(EmployeeDB.department).all()
    
    department_counts = {dept: count for dept, count in results}
    
    return department_counts


@router.get("/payroll-by-department")
async def get_payroll_by_department(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get total payroll amount grouped by department"""
    
    # Get all employees with their departments
    employees = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE,
        EmployeeDB.department.isnot(None)
    ).all()
    
    department_payroll = {}
    
    for employee in employees:
        # Get latest payroll entry for this employee
        latest_entry = db.query(PayrollEntryDB).filter(
            PayrollEntryDB.employee_id == employee.id
        ).order_by(PayrollEntryDB.created_at.desc()).first()
        
        if latest_entry:
            dept = employee.department
            if dept not in department_payroll:
                department_payroll[dept] = 0
            department_payroll[dept] += latest_entry.net
    
    # Round values
    return {dept: round(amount, 2) for dept, amount in department_payroll.items()}


@router.get("/department-attendance-rates")
async def get_department_attendance_rates(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance rates by department for the last N days"""
    
    start_date = date.today() - timedelta(days=days)
    
    # Get all active employees by department
    employees = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE,
        EmployeeDB.department.isnot(None)
    ).all()
    
    department_stats = {}
    
    for employee in employees:
        dept = employee.department
        if dept not in department_stats:
            department_stats[dept] = {'total_days': 0, 'present_days': 0}
        
        # Count working days (assuming 5 days/week)
        working_days = days * 5 // 7
        department_stats[dept]['total_days'] += working_days
        
        # Count present days
        present = db.query(AttendanceDB).filter(
            AttendanceDB.employee_id == employee.id,
            AttendanceDB.date >= start_date
        ).count()
        
        department_stats[dept]['present_days'] += present
    
    # Calculate rates
    rates = {}
    for dept, stats in department_stats.items():
        if stats['total_days'] > 0:
            rate = (stats['present_days'] / stats['total_days']) * 100
            rates[dept] = round(rate, 1)
        else:
            rates[dept] = 0.0
    
    return rates


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent activity across the system"""
    
    # Recent attendance (today)
    today = date.today()
    recent_attendance_records = db.query(AttendanceDB).filter(
        AttendanceDB.date == today
    ).order_by(AttendanceDB.created_at.desc()).limit(limit).all()
    
    recent_attendance = []
    for att in recent_attendance_records:
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == att.employee_id).first()
        if employee:
            status = "present"
            if att.time_in > "09:00":
                status = "late"
            
            recent_attendance.append({
                "id": att.id,
                "employeeName": employee.name,
                "date": att.date.isoformat(),
                "status": status,
                "checkIn": att.time_in
            })
    
    # Add absent employees
    all_active = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE
    ).all()
    
    present_ids = {att.employee_id for att in recent_attendance_records}
    absent_employees = [emp for emp in all_active if emp.id not in present_ids]
    
    for emp in absent_employees[:limit - len(recent_attendance)]:
        recent_attendance.append({
            "id": emp.id,
            "employeeName": emp.name,
            "date": today.isoformat(),
            "status": "absent",
            "checkIn": None
        })
    
    # Recent payroll runs
    recent_payrolls = db.query(PayrollRunDB).order_by(
        PayrollRunDB.created_at.desc()
    ).limit(limit).all()
    
    payroll_data = []
    for run in recent_payrolls:
        entries = db.query(PayrollEntryDB).filter(
            PayrollEntryDB.payroll_run_id == run.id
        ).all()
        
        total_amount = sum(entry.net for entry in entries)
        
        payroll_data.append({
            "id": run.id,
            "period": f"{run.start_date.strftime('%B %Y')}",
            "amount": round(total_amount, 2),
            "employeeCount": len(entries),
            "createdAt": run.created_at.isoformat()
        })
    
    # Recent employees
    recent_employees = db.query(EmployeeDB).order_by(
        EmployeeDB.created_at.desc()
    ).limit(limit).all()
    
    employee_data = []
    for emp in recent_employees:
        employee_data.append({
            "id": emp.id,
            "name": emp.name,
            "role": emp.role,
            "department": emp.department,
            "joinDate": emp.created_at.date().isoformat()
        })
    
    return {
        "recentAttendance": recent_attendance,
        "recentPayrolls": payroll_data,
        "recentEmployees": employee_data
    }