from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from models.attendance import AttendanceDB
from models.employee import EmployeeDB
from models.leaves import LeaveDB
from services.attendance_calculator import AttendanceCalculator
from services.holiday_calculator import HolidayCalculator
from utils.constants import ShiftType, AttendanceStatus, LeaveStatus, SalaryType
from pydantic import BaseModel
import uuid
import pandas as pd
import io

router = APIRouter(prefix="/attendance", tags=["Attendance"])

class AttendanceCreate(BaseModel):
    employee_id: str
    date: date
    time_in: Optional[str] = None
    time_out: Optional[str] = None
    shift_type: ShiftType
    overtime_hours: float = 0.0
    nightshift_hours: float = 0.0
    notes: Optional[str] = None
    expected_time_in: str = "08:00"
    expected_time_out: str = "17:00"

class AttendanceUpdate(BaseModel):
    date: Optional[str] = None
    time_in: Optional[str] = None
    time_out: Optional[str] = None
    shift_type: Optional[ShiftType] = None
    overtime_hours: Optional[float] = None
    nightshift_hours: Optional[float] = None
    notes: Optional[str] = None

@router.post("")
async def create_attendance(
    attendance_create: AttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create attendance record with automatic deduction calculations"""
    
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == attendance_create.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if employee is on approved leave
    leave = db.query(LeaveDB).filter(
        LeaveDB.employee_id == attendance_create.employee_id,
        LeaveDB.start_date <= attendance_create.date,
        LeaveDB.end_date >= attendance_create.date,
        LeaveDB.status == LeaveStatus.APPROVED
    ).first()
    
    if leave:
        # Employee is on leave, mark as ON_LEAVE
        new_attendance = AttendanceDB(
            id=str(uuid.uuid4()),
            employee_id=attendance_create.employee_id,
            date=attendance_create.date,
            time_in=None,
            time_out=None,
            shift_type=attendance_create.shift_type,
            status=AttendanceStatus.ON_LEAVE,
            regular_hours=0,
            late_deduction=0,
            absent_deduction=0,
            undertime_deduction=0
        )
        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)
        return new_attendance
    
    # Calculate hourly rate based on salary type
    if employee.salary_type == SalaryType.HOURLY:
        hourly_rate = employee.salary_rate
    elif employee.salary_type == SalaryType.DAILY:
        hourly_rate = employee.salary_rate / 8
    else:  # MONTHLY
        hourly_rate = (employee.salary_rate / 30) / 8
    
    daily_rate = hourly_rate * 8
    
    # Check if it's a holiday
    is_holiday, holiday_id, holiday_type = HolidayCalculator.is_holiday(db, attendance_create.date)
    
    # Calculate attendance metrics
    if not attendance_create.time_in:
        # Absent
        status = AttendanceStatus.ABSENT
        late_minutes = 0
        undertime_minutes = 0
        regular_hours = 0
        late_deduction = 0
        undertime_deduction = 0
        absent_deduction = AttendanceCalculator.calculate_absent_deduction(daily_rate)
    else:
        # Present
        late_minutes = AttendanceCalculator.calculate_late_minutes(
            attendance_create.time_in,
            attendance_create.expected_time_in
        )
        
        undertime_minutes = 0
        if attendance_create.time_out:
            undertime_minutes = AttendanceCalculator.calculate_undertime_minutes(
                attendance_create.time_out,
                attendance_create.expected_time_out
            )
        
        # Calculate regular hours
        from services.payroll_calculator import PayrollCalculator
        regular_hours = PayrollCalculator.calculate_work_hours(
            attendance_create.time_in,
            attendance_create.time_out or "17:00"
        )
        
        # Determine status
        status = AttendanceCalculator.determine_status(
            attendance_create.time_in,
            attendance_create.time_out,
            late_minutes,
            undertime_minutes,
            regular_hours
        )
        
        # Calculate deductions
        late_deduction = AttendanceCalculator.calculate_late_deduction(late_minutes, hourly_rate)
        undertime_deduction = AttendanceCalculator.calculate_undertime_deduction(undertime_minutes, hourly_rate)
        absent_deduction = 0
    
    # Create attendance record
    new_attendance = AttendanceDB(
        id=str(uuid.uuid4()),
        employee_id=attendance_create.employee_id,
        date=attendance_create.date,
        time_in=attendance_create.time_in,
        time_out=attendance_create.time_out,
        shift_type=attendance_create.shift_type,
        regular_hours=round(regular_hours, 2),
        overtime_hours=attendance_create.overtime_hours,
        nightshift_hours=attendance_create.nightshift_hours,
        status=status,
        late_minutes=round(late_minutes, 2),
        undertime_minutes=round(undertime_minutes, 2),
        late_deduction=late_deduction,
        absent_deduction=absent_deduction,
        undertime_deduction=undertime_deduction,
        is_holiday=is_holiday,
        holiday_id=holiday_id,
        notes=attendance_create.notes
    )
    
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)
    
    return new_attendance

@router.get("")
async def get_attendance(
    page: int = 1,
    limit: int = 10,
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[AttendanceStatus] = None,
    sort_by: Optional[str] = "date",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance records with pagination and filters"""
    query = db.query(AttendanceDB)
    
    if employee_id:
        query = query.filter(AttendanceDB.employee_id == employee_id)
    if start_date and end_date:
        query = query.filter(AttendanceDB.date >= start_date, AttendanceDB.date <= end_date)
    if status:
        query = query.filter(AttendanceDB.status == status)
    
    total = query.count()
    skip = (page - 1) * limit
    
    sort_column = getattr(AttendanceDB, sort_by, AttendanceDB.date)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    attendance_records = query.offset(skip).limit(limit).all()
    
    return {
        "data": attendance_records,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@router.get("/{attendance_id}")
async def get_attendance_by_id(
    attendance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance by ID"""
    attendance = db.query(AttendanceDB).filter(AttendanceDB.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return attendance

@router.put("/{attendance_id}")
async def update_attendance(
    attendance_id: str,
    attendance_update: AttendanceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update attendance record and recalculate deductions"""
    attendance = db.query(AttendanceDB).filter(AttendanceDB.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    update_data = attendance_update.dict(exclude_unset=True)
    
    # Convert date string to date object if present
    if 'date' in update_data and update_data['date'] is not None:
        update_data['date'] = datetime.fromisoformat(update_data['date']).date()
    
    # If time_in or time_out changed, recalculate everything
    if 'time_in' in update_data or 'time_out' in update_data:
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == attendance.employee_id).first()
        
        # Calculate hourly rate
        if employee.salary_type == SalaryType.HOURLY:
            hourly_rate = employee.salary_rate
        elif employee.salary_type == SalaryType.DAILY:
            hourly_rate = employee.salary_rate / 8
        else:
            hourly_rate = (employee.salary_rate / 30) / 8
        
        time_in = update_data.get('time_in', attendance.time_in)
        time_out = update_data.get('time_out', attendance.time_out)
        
        if time_in:
            late_minutes = AttendanceCalculator.calculate_late_minutes(time_in, "08:00")
            update_data['late_minutes'] = late_minutes
            update_data['late_deduction'] = AttendanceCalculator.calculate_late_deduction(late_minutes, hourly_rate)
        
        if time_out:
            undertime_minutes = AttendanceCalculator.calculate_undertime_minutes(time_out, "17:00")
            update_data['undertime_minutes'] = undertime_minutes
            update_data['undertime_deduction'] = AttendanceCalculator.calculate_undertime_deduction(undertime_minutes, hourly_rate)
    
    for field, value in update_data.items():
        if value is not None:
            setattr(attendance, field, value)
    
    db.commit()
    db.refresh(attendance)
    
    return attendance

@router.delete("/{attendance_id}")
async def delete_attendance(
    attendance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete attendance record"""
    attendance = db.query(AttendanceDB).filter(AttendanceDB.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    db.delete(attendance)
    db.commit()
    
    return {"message": "Attendance record deleted successfully"}

@router.get("/employee/{employee_id}/summary")
async def get_employee_attendance_summary(
    employee_id: str,
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get attendance summary for an employee"""
    
    records = db.query(AttendanceDB).filter(
        AttendanceDB.employee_id == employee_id,
        AttendanceDB.date >= start_date,
        AttendanceDB.date <= end_date
    ).all()
    
    summary = {
        "total_days": len(records),
        "present": sum(1 for r in records if r.status == AttendanceStatus.PRESENT),
        "late": sum(1 for r in records if r.status == AttendanceStatus.LATE),
        "absent": sum(1 for r in records if r.status == AttendanceStatus.ABSENT),
        "undertime": sum(1 for r in records if r.status == AttendanceStatus.UNDERTIME),
        "half_day": sum(1 for r in records if r.status == AttendanceStatus.HALF_DAY),
        "on_leave": sum(1 for r in records if r.status == AttendanceStatus.ON_LEAVE),
        "total_late_minutes": sum(r.late_minutes for r in records),
        "total_undertime_minutes": sum(r.undertime_minutes for r in records),
        "total_late_deduction": sum(r.late_deduction for r in records),
        "total_absent_deduction": sum(r.absent_deduction for r in records),
        "total_undertime_deduction": sum(r.undertime_deduction for r in records),
        "total_deductions": sum(r.late_deduction + r.absent_deduction + r.undertime_deduction for r in records)
    }
    
    return summary


@router.post("/import")
async def import_attendance(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Import attendance from Excel/CSV file
    Expected columns: employee_id, date, time_in, time_out, shift_type
    Optional columns: overtime_hours, nightshift_hours, notes
    """
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls) or CSV files are allowed")
    
    try:
        # Read file
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
        required_columns = ['employee_id', 'date', 'time_in', 'time_out', 'shift_type']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Process each row
        imported = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Validate employee exists
                employee = db.query(EmployeeDB).filter(
                    EmployeeDB.id == str(row['employee_id'])
                ).first()
                
                if not employee:
                    errors.append({
                        "row": index + 2,  # +2 because of header and 0-indexing
                        "error": f"Employee ID {row['employee_id']} not found"
                    })
                    continue
                
                # Parse date
                if isinstance(row['date'], str):
                    attendance_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                else:
                    attendance_date = row['date']
                
                # Check for duplicates
                existing = db.query(AttendanceDB).filter(
                    AttendanceDB.employee_id == str(row['employee_id']),
                    AttendanceDB.date == attendance_date
                ).first()
                
                if existing:
                    errors.append({
                        "row": index + 2,
                        "error": f"Attendance for {row['employee_id']} on {attendance_date} already exists"
                    })
                    continue
                
                # Parse shift type
                try:
                    shift_type = ShiftType(row['shift_type'].upper())
                except:
                    shift_type = ShiftType.DAY
                
                # Create attendance data
                attendance_data = AttendanceCreate(
                    employee_id=str(row['employee_id']),
                    date=attendance_date,
                    time_in=str(row['time_in']) if pd.notna(row['time_in']) else None,
                    time_out=str(row['time_out']) if pd.notna(row['time_out']) else None,
                    shift_type=shift_type,
                    overtime_hours=float(row.get('overtime_hours', 0)) if pd.notna(row.get('overtime_hours')) else 0.0,
                    nightshift_hours=float(row.get('nightshift_hours', 0)) if pd.notna(row.get('nightshift_hours')) else 0.0,
                    notes=str(row.get('notes', '')) if pd.notna(row.get('notes')) else None
                )
                
                # Use existing create_attendance logic
                # Calculate hourly rate
                if employee.salary_type == SalaryType.HOURLY:
                    hourly_rate = employee.salary_rate
                elif employee.salary_type == SalaryType.DAILY:
                    hourly_rate = employee.salary_rate / 8
                else:
                    hourly_rate = (employee.salary_rate / 30) / 8
                
                daily_rate = hourly_rate * 8
                
                # Check if on leave
                leave = db.query(LeaveDB).filter(
                    LeaveDB.employee_id == str(row['employee_id']),
                    LeaveDB.start_date <= attendance_date,
                    LeaveDB.end_date >= attendance_date,
                    LeaveDB.status == LeaveStatus.APPROVED
                ).first()
                
                if leave:
                    status = AttendanceStatus.ON_LEAVE
                    late_minutes = 0
                    undertime_minutes = 0
                    regular_hours = 0
                    late_deduction = 0
                    undertime_deduction = 0
                    absent_deduction = 0
                elif not attendance_data.time_in:
                    status = AttendanceStatus.ABSENT
                    late_minutes = 0
                    undertime_minutes = 0
                    regular_hours = 0
                    late_deduction = 0
                    undertime_deduction = 0
                    absent_deduction = AttendanceCalculator.calculate_absent_deduction(daily_rate)
                else:
                    late_minutes = AttendanceCalculator.calculate_late_minutes(
                        attendance_data.time_in, "08:00"
                    )
                    
                    undertime_minutes = 0
                    if attendance_data.time_out:
                        undertime_minutes = AttendanceCalculator.calculate_undertime_minutes(
                            attendance_data.time_out, "17:00"
                        )
                    
                    from services.payroll_calculator import PayrollCalculator
                    regular_hours = PayrollCalculator.calculate_work_hours(
                        attendance_data.time_in,
                        attendance_data.time_out or "17:00"
                    )
                    
                    status = AttendanceCalculator.determine_status(
                        attendance_data.time_in,
                        attendance_data.time_out,
                        late_minutes,
                        undertime_minutes,
                        regular_hours
                    )
                    
                    late_deduction = AttendanceCalculator.calculate_late_deduction(
                        late_minutes, hourly_rate
                    )
                    undertime_deduction = AttendanceCalculator.calculate_undertime_deduction(
                        undertime_minutes, hourly_rate
                    )
                    absent_deduction = 0
                
                # Check holiday
                is_holiday, holiday_id, _ = HolidayCalculator.is_holiday(db, attendance_date)
                
                # Create record
                new_attendance = AttendanceDB(
                    id=str(uuid.uuid4()),
                    employee_id=str(row['employee_id']),
                    date=attendance_date,
                    time_in=attendance_data.time_in,
                    time_out=attendance_data.time_out,
                    shift_type=shift_type,
                    regular_hours=round(regular_hours, 2),
                    overtime_hours=attendance_data.overtime_hours,
                    nightshift_hours=attendance_data.nightshift_hours,
                    status=status,
                    late_minutes=round(late_minutes, 2),
                    undertime_minutes=round(undertime_minutes, 2),
                    late_deduction=late_deduction,
                    absent_deduction=absent_deduction,
                    undertime_deduction=undertime_deduction,
                    is_holiday=is_holiday,
                    holiday_id=holiday_id,
                    notes=attendance_data.notes
                )
                
                db.add(new_attendance)
                imported.append({
                    "employee_id": str(row['employee_id']),
                    "employee_name": employee.name,
                    "date": attendance_date.isoformat()
                })
                
            except Exception as e:
                errors.append({
                    "row": index + 2,
                    "error": str(e)
                })
        
        db.commit()
        
        return {
            "message": f"Import completed. {len(imported)} records imported, {len(errors)} errors",
            "imported_count": len(imported),
            "error_count": len(errors),
            "imported": imported,
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@router.get("/import/template")
async def download_import_template(
    current_user: User = Depends(get_current_user)
):
    """Download CSV template for attendance import"""
    
    template_data = {
        "employee_id": ["EMP001", "EMP002"],
        "date": ["2025-01-15", "2025-01-15"],
        "time_in": ["08:00", "08:30"],
        "time_out": ["17:00", "17:30"],
        "shift_type": ["DAY", "DAY"],
        "overtime_hours": [0, 1.5],
        "nightshift_hours": [0, 0],
        "notes": ["", "Approved OT"]
    }
    
    df = pd.DataFrame(template_data)
    
    # Convert to CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_import_template.csv"}
    )