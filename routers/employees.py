from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from models.employee import EmployeeDB
from utils.constants import EmployeeStatus, SalaryType
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/employees", tags=["Employees"])

class EmployeeCreate(BaseModel):
    name: str
    contact: str
    role: str
    department: Optional[str] = None
    salary_type: SalaryType
    salary_rate: float
    benefits: Optional[dict] = None
    taxes: Optional[dict] = None
    overtime_rate: Optional[float] = None
    nightshift_rate: Optional[float] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    salary_type: Optional[SalaryType] = None
    salary_rate: Optional[float] = None
    benefits: Optional[dict] = None
    taxes: Optional[dict] = None
    overtime_rate: Optional[float] = None
    nightshift_rate: Optional[float] = None
    status: Optional[EmployeeStatus] = None

@router.get("")
async def get_employees(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all employees with pagination, search, and filters"""
    query = db.query(EmployeeDB)
    
    if search:
        query = query.filter(
            (EmployeeDB.name.ilike(f"%{search}%")) |
            (EmployeeDB.role.ilike(f"%{search}%")) |
            (EmployeeDB.department.ilike(f"%{search}%"))
        )
    
    if status:
        query = query.filter(EmployeeDB.status == status)
    
    total = query.count()
    skip = (page - 1) * limit
    
    sort_column = getattr(EmployeeDB, sort_by, EmployeeDB.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    employees = query.offset(skip).limit(limit).all()
    
    return {
        "data": employees,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@router.get("/{employee_id}")
async def get_employee(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get employee by ID"""
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@router.post("")
async def create_employee(
    employee_create: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new employee"""
    new_employee = EmployeeDB(
        id=str(uuid.uuid4()),
        **employee_create.dict()
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@router.put("/{employee_id}")
async def update_employee(
    employee_id: str,
    employee_update: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update employee"""
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    
    db.commit()
    db.refresh(employee)
    return employee

@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete employee (set to inactive)"""
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee.status = EmployeeStatus.INACTIVE
    db.commit()
    return {"message": "Employee deactivated successfully"}