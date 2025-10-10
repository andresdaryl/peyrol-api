from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User
from models.employee import EmployeeDB
from models.leaves import LeaveBalanceDB
from utils.constants import EmployeeStatus, SalaryType, UserRole, LeaveCredits
from schemas.employees import EmployeeCreate, EmployeeUpdate
from datetime import date
import uuid
import shutil
from pathlib import Path

router = APIRouter(prefix="/employees", tags=["Employees"])

# Create uploads directory
UPLOAD_DIR = Path("uploads/employee_profiles")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/{employee_id}/upload-image")
async def upload_employee_image(
    employee_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload employee profile image"""
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")
    
    # Validate file size (max 5MB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Delete old image if exists
    if employee.profile_image_url:
        old_path = Path(employee.profile_image_url)
        if old_path.exists():
            old_path.unlink()
    
    # Save new image
    file_extension = file.filename.split(".")[-1]
    new_filename = f"{employee_id}.{file_extension}"
    file_path = UPLOAD_DIR / new_filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update employee record
    employee.profile_image_url = str(file_path)
    db.commit()
    db.refresh(employee)
    
    return {
        "message": "Profile image uploaded successfully",
        "image_url": str(file_path)
    }

@router.delete("/{employee_id}/image")
async def delete_employee_image(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete employee profile image"""
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.profile_image_url:
        file_path = Path(employee.profile_image_url)
        if file_path.exists():
            file_path.unlink()
        
        employee.profile_image_url = None
        db.commit()
        db.refresh(employee)
    
    return {"message": "Profile image deleted successfully"}

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


@router.post("/initialize-balance/{employee_id}")
async def initialize_leave_balance(
    employee_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Initialize leave balance for new employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if balance already exists
    existing = db.query(LeaveBalanceDB).filter(
        LeaveBalanceDB.employee_id == employee_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Leave balance already exists")
    
    # Calculate prorated credits based on hire date
    from datetime import datetime
    hire_date = employee.created_at.date()
    current_year = datetime.now().year
    
    # If hired mid-year, prorate the credits
    days_remaining = (date(current_year, 12, 31) - hire_date).days
    prorate_factor = days_remaining / 365
    
    sick_credits = round(LeaveCredits.SICK_LEAVE_ANNUAL * prorate_factor, 1)
    vacation_credits = round(LeaveCredits.VACATION_LEAVE_ANNUAL * prorate_factor, 1)
    
    # Create balance
    new_balance = LeaveBalanceDB(
        id=str(uuid.uuid4()),
        employee_id=employee_id,
        year=current_year,
        sick_leave_balance=sick_credits,
        vacation_leave_balance=vacation_credits,
        sick_leave_used=0,
        vacation_leave_used=0
    )
    
    db.add(new_balance)
    db.commit()
    db.refresh(new_balance)
    
    return {
        "message": "Leave balance initialized",
        "employee_id": employee_id,
        "year": current_year,
        "sick_leave_credits": sick_credits,
        "vacation_leave_credits": vacation_credits,
        "prorated": prorate_factor < 1,
        "hire_date": hire_date.isoformat()
    }


@router.post("/assign-credits")
async def assign_leave_credits(
    employee_id: str,
    sick_leave: float,
    vacation_leave: float,
    reason: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Manually assign/adjust leave credits (HR override)"""
    
    balance = db.query(LeaveBalanceDB).filter(
        LeaveBalanceDB.employee_id == employee_id
    ).first()
    
    if not balance:
        raise HTTPException(status_code=404, detail="Leave balance not found. Initialize first.")
    
    # Apply caps
    new_sick = min(balance.sick_leave_balance + sick_leave, LeaveCredits.MAX_ACCUMULATED_SICK_LEAVE)
    new_vacation = min(balance.vacation_leave_balance + vacation_leave, LeaveCredits.MAX_ACCUMULATED_VACATION_LEAVE)
    
    old_sick = balance.sick_leave_balance
    old_vacation = balance.vacation_leave_balance
    
    balance.sick_leave_balance = new_sick
    balance.vacation_leave_balance = new_vacation
    
    db.commit()
    db.refresh(balance)
    
    return {
        "message": "Leave credits adjusted",
        "employee_id": employee_id,
        "changes": {
            "sick_leave": {
                "old": old_sick,
                "adjustment": sick_leave,
                "new": new_sick
            },
            "vacation_leave": {
                "old": old_vacation,
                "adjustment": vacation_leave,
                "new": new_vacation
            }
        },
        "adjusted_by": current_user.email,
        "reason": reason
    }


@router.post("/bulk-initialize")
async def bulk_initialize_leave_balances(
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Initialize leave balances for all employees without one"""
    
    from datetime import datetime
    
    # Get all active employees
    employees = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE
    ).all()
    
    initialized = []
    skipped = []
    
    for employee in employees:
        # Check if balance exists
        existing = db.query(LeaveBalanceDB).filter(
            LeaveBalanceDB.employee_id == employee.id
        ).first()
        
        if existing:
            skipped.append(employee.id)
            continue
        
        # Calculate prorated credits
        hire_date = employee.created_at.date()
        current_year = datetime.now().year
        days_remaining = (date(current_year, 12, 31) - hire_date).days
        prorate_factor = max(0, min(1, days_remaining / 365))
        
        sick_credits = round(LeaveCredits.SICK_LEAVE_ANNUAL * prorate_factor, 1)
        vacation_credits = round(LeaveCredits.VACATION_LEAVE_ANNUAL * prorate_factor, 1)
        
        # Create balance
        new_balance = LeaveBalanceDB(
            id=str(uuid.uuid4()),
            employee_id=employee.id,
            year=current_year,
            sick_leave_balance=sick_credits,
            vacation_leave_balance=vacation_credits
        )
        
        db.add(new_balance)
        initialized.append({
            "employee_id": employee.id,
            "employee_name": employee.name,
            "sick_credits": sick_credits,
            "vacation_credits": vacation_credits
        })
    
    db.commit()
    
    return {
        "message": f"Initialized {len(initialized)} leave balances",
        "initialized_count": len(initialized),
        "skipped_count": len(skipped),
        "details": initialized
    }


@router.post("/annual-reset")
async def annual_leave_reset(
    year: int,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """
    Annual leave reset (run at start of year)
    - Adds new year's credits
    - Applies carryover limits
    - Resets usage counters
    """
    
    balances = db.query(LeaveBalanceDB).all()
    reset_count = 0
    
    for balance in balances:
        # Calculate new balances with carryover
        new_sick = min(
            balance.sick_leave_balance + LeaveCredits.SICK_LEAVE_ANNUAL,
            LeaveCredits.MAX_ACCUMULATED_SICK_LEAVE
        )
        new_vacation = min(
            balance.vacation_leave_balance + LeaveCredits.VACATION_LEAVE_ANNUAL,
            LeaveCredits.MAX_ACCUMULATED_VACATION_LEAVE
        )
        
        # Update balance
        balance.year = year
        balance.sick_leave_balance = new_sick
        balance.vacation_leave_balance = new_vacation
        balance.sick_leave_used = 0
        balance.vacation_leave_used = 0
        
        reset_count += 1
    
    db.commit()
    
    return {
        "message": f"Annual leave reset completed for {reset_count} employees",
        "year": year,
        "reset_count": reset_count,
        "credits_added": {
            "sick_leave": LeaveCredits.SICK_LEAVE_ANNUAL,
            "vacation_leave": LeaveCredits.VACATION_LEAVE_ANNUAL
        }
    }


@router.get("/balance-summary")
async def get_all_leave_balances(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Get leave balance summary for all employees"""
    
    balances = db.query(LeaveBalanceDB).all()
    
    summary = []
    for balance in balances:
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == balance.employee_id).first()
        if employee:
            summary.append({
                "employee_id": balance.employee_id,
                "employee_name": employee.name,
                "department": employee.department,
                "year": balance.year,
                "sick_leave": {
                    "balance": balance.sick_leave_balance,
                    "used": balance.sick_leave_used,
                    "total": balance.sick_leave_balance + balance.sick_leave_used
                },
                "vacation_leave": {
                    "balance": balance.vacation_leave_balance,
                    "used": balance.vacation_leave_used,
                    "total": balance.vacation_leave_balance + balance.vacation_leave_used
                }
            })
    
    return {
        "total_employees": len(summary),
        "balances": summary
    }


@router.post("/{employee_id}/initialize-leaves")
async def auto_initialize_leaves_on_create(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-initialize leave balance when employee is created"""
    
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if already initialized
    existing = db.query(LeaveBalanceDB).filter(
        LeaveBalanceDB.employee_id == employee_id
    ).first()
    
    if existing:
        return {"message": "Leave balance already exists", "balance": existing}
    
    # Calculate prorated credits
    from datetime import datetime
    hire_date = employee.created_at.date()
    current_year = datetime.now().year
    
    days_remaining = (date(current_year, 12, 31) - hire_date).days
    prorate_factor = max(0, min(1, days_remaining / 365))
    
    sick_credits = round(LeaveCredits.SICK_LEAVE_ANNUAL * prorate_factor, 1)
    vacation_credits = round(LeaveCredits.VACATION_LEAVE_ANNUAL * prorate_factor, 1)
    
    # Create balance
    new_balance = LeaveBalanceDB(
        id=str(uuid.uuid4()),
        employee_id=employee_id,
        year=current_year,
        sick_leave_balance=sick_credits,
        vacation_leave_balance=vacation_credits
    )
    
    db.add(new_balance)
    db.commit()
    db.refresh(new_balance)
    
    return {
        "message": "Leave balance initialized automatically",
        "employee_id": employee_id,
        "sick_leave": sick_credits,
        "vacation_leave": vacation_credits,
        "prorated": prorate_factor < 1
    }

@router.put("/{employee_id}/allowances")
async def update_employee_allowances(
    employee_id: str,
    allowances: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update employee allowances specifically"""
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    for key, value in allowances.items():
        if not isinstance(value, (int, float)) or value < 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid allowance value for '{key}'. Must be a positive number."
            )
    
    old_allowances = employee.allowances or {}
    employee.allowances = allowances
    
    db.commit()
    db.refresh(employee)
    
    return {
        "message": "Allowances updated successfully",
        "employee_id": employee_id,
        "old_allowances": old_allowances,
        "new_allowances": allowances,
        "total_allowances": sum(allowances.values())
    }

@router.put("/{employee_id}/taxes")
async def update_employee_taxes(
    employee_id: str,
    taxes: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update employee-specific tax deductions/exemptions"""
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate taxes (all values must be numbers)
    for key, value in taxes.items():
        if not isinstance(value, (int, float)):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid tax value for '{key}'. Must be a number."
            )
    
    old_taxes = employee.taxes or {}
    employee.taxes = taxes
    
    db.commit()
    db.refresh(employee)
    
    return {
        "message": "Employee taxes updated successfully",
        "employee_id": employee_id,
        "old_taxes": old_taxes,
        "new_taxes": taxes,
        "total_additional_deductions": sum(v for k, v in taxes.items() if v > 0)
    }

@router.get("/{employee_id}/tax-preview")
async def preview_employee_tax(
    employee_id: str,
    estimated_monthly_gross: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Preview employee's tax calculation"""
    from services.tax_calculator import TaxCalculator
    from services.benefits_calculator import BenefitsCalculator
    
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Use estimated gross or calculate from salary
    if not estimated_monthly_gross:
        if employee.salary_type == SalaryType.MONTHLY:
            estimated_monthly_gross = employee.salary_rate
        elif employee.salary_type == SalaryType.DAILY:
            estimated_monthly_gross = employee.salary_rate * 22
        elif employee.salary_type == SalaryType.HOURLY:
            estimated_monthly_gross = employee.salary_rate * 8 * 22
    
    # Calculate contributions
    contributions = BenefitsCalculator.calculate_all_contributions(estimated_monthly_gross, db)
    
    # Calculate tax
    tax_info = TaxCalculator.calculate_tax_for_payroll(
        gross_pay=estimated_monthly_gross,
        mandatory_contributions=contributions,
        db=db
    )
    
    # Include custom deductions
    custom_deductions = sum((employee.taxes or {}).values())
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.name,
        "estimated_monthly_gross": estimated_monthly_gross,
        "mandatory_contributions": {
            "sss": contributions['sss']['employee'],
            "philhealth": contributions['philhealth']['employee'],
            "pagibig": contributions['pagibig']['employee'],
            "total": contributions['total_employee']
        },
        "withholding_tax": tax_info['withholding_tax'],
        "custom_deductions": employee.taxes or {},
        "total_custom_deductions": custom_deductions,
        "total_deductions": contributions['total_employee'] + tax_info['withholding_tax'] + custom_deductions,
        "estimated_net_pay": estimated_monthly_gross - contributions['total_employee'] - tax_info['withholding_tax'] - custom_deductions
    }