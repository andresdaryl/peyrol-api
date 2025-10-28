from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User
from models.holidays import HolidayDB
from utils.constants import HolidayType, UserRole
from schemas.holidays import HolidayCreate, HolidayUpdate, HolidayResponse
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/holidays", tags=["Holidays"])

@router.post("", response_model=HolidayResponse)
async def create_holiday(
    holiday_data: HolidayCreate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Create a holiday"""
    
    # Check if holiday already exists for this date
    existing = db.query(HolidayDB).filter(HolidayDB.date == holiday_data.date).first()
    if existing:
        raise HTTPException(status_code=400, detail="Holiday already exists for this date")
    
    new_holiday = HolidayDB(
        id=str(uuid.uuid4()),
        **holiday_data.dict()
    )
    
    db.add(new_holiday)
    db.commit()
    db.refresh(new_holiday)
    
    return new_holiday

@router.get("", response_model=List[HolidayResponse])
async def get_holidays(
    year: Optional[int] = None,
    month: Optional[int] = None,
    holiday_type: Optional[HolidayType] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get holidays with optional filters"""
    from sqlalchemy import extract
    
    query = db.query(HolidayDB)
    
    if year:
        query = query.filter(extract('year', HolidayDB.date) == year)
    if month:
        query = query.filter(extract('month', HolidayDB.date) == month)
    if holiday_type:
        query = query.filter(HolidayDB.holiday_type == holiday_type)
    
    holidays = query.order_by(HolidayDB.date).all()
    return holidays

@router.put("/{holiday_id}", response_model=HolidayResponse)
async def update_holiday(
    holiday_id: str,
    holiday_update: HolidayUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Update holiday"""
    
    holiday = db.query(HolidayDB).filter(HolidayDB.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    update_data = holiday_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(holiday, field, value)
    
    db.commit()
    db.refresh(holiday)
    
    return holiday

@router.delete("/{holiday_id}")
async def delete_holiday(
    holiday_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Delete holiday"""
    
    holiday = db.query(HolidayDB).filter(HolidayDB.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    db.delete(holiday)
    db.commit()
    
    return {"message": "Holiday deleted successfully"}

@router.post("/bulk-create")
async def bulk_create_holidays(
    holidays: List[HolidayCreate],
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Bulk create holidays (useful for yearly setup)"""
    
    created = []
    for holiday_data in holidays:
        # Skip if already exists
        existing = db.query(HolidayDB).filter(HolidayDB.date == holiday_data.date).first()
        if not existing:
            new_holiday = HolidayDB(
                id=str(uuid.uuid4()),
                **holiday_data.dict()
            )
            db.add(new_holiday)
            created.append(new_holiday)
    
    db.commit()
    
    return {
        "message": f"Created {len(created)} holidays",
        "created": len(created),
        "skipped": len(holidays) - len(created)
    }