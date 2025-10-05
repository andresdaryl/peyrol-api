from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from models.attendance import AttendanceDB
from models.employee import EmployeeDB
from utils.constants import ShiftType
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/attendance", tags=["Attendance"])

class AttendanceCreate(BaseModel):
    employee_id: str
    date: date
    time_in: str
    time_out: str
    shift_type: ShiftType
    overtime_hours: float = 0.0
    nightshift_hours: float = 0.0
    notes: Optional[str] = None

class AttendanceUpdate(BaseModel):
    date: Optional[str] = None
    time_in: Optional[str] = None
    time_out: Optional[str] = None
    shift_type: Optional[ShiftType] = None
    overtime_hours: Optional[float] = None
    nightshift_hours: Optional[float] = None
    notes: Optional[str] = None

@router.get("")
async def get_attendance(
    page: int = 1,
    limit: int = 10,
    employee_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
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

@router.post("")
async def create_attendance(
    attendance_create: AttendanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create attendance record"""
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == attendance_create.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    new_attendance = AttendanceDB(
        id=str(uuid.uuid4()),
        **attendance_create.dict()
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)
    return new_attendance

@router.put("/{attendance_id}")
async def update_attendance(
    attendance_id: str,
    attendance_update: AttendanceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update attendance record"""
    attendance = db.query(AttendanceDB).filter(AttendanceDB.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    update_data = attendance_update.dict(exclude_unset=True)
    
    if 'date' in update_data and update_data['date'] is not None:
        update_data['date'] = datetime.fromisoformat(update_data['date']).date()
    
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