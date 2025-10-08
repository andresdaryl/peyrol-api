from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, timezone
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User
from models.leaves import LeaveDB, LeaveBalanceDB
from models.employee import EmployeeDB
from services.leave_calculator import LeaveCalculator
from utils.constants import LeaveType, LeaveStatus, UserRole, LeaveCredits, EmployeeStatus
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/leaves", tags=["Leaves"])

# Schemas
class LeaveCreate(BaseModel):
    employee_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None
    attachment_url: Optional[str] = None

class LeaveUpdate(BaseModel):
    status: Optional[LeaveStatus] = None
    rejection_reason: Optional[str] = None

class LeaveResponse(BaseModel):
    id: str
    employee_id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    days_count: int
    reason: Optional[str]
    status: LeaveStatus
    approved_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class LeaveCreditsAssignment(BaseModel):
    employee_id: str
    sick_leave: float
    vacation_leave: float
    reason: Optional[str] = None        

# Routes
@router.post("", response_model=LeaveResponse)
async def request_leave(
    leave_data: LeaveCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request a leave"""
    
    # Verify employee exists
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == leave_data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Calculate working days
    days_count = LeaveCalculator.calculate_working_days(
        leave_data.start_date,
        leave_data.end_date,
        db
    )
    
    # Check leave balance for paid leaves
    if leave_data.leave_type in [LeaveType.SICK_LEAVE, LeaveType.VACATION_LEAVE]:
        has_balance, available = LeaveCalculator.check_leave_balance(
            db, leave_data.employee_id, leave_data.leave_type, days_count
        )
        if not has_balance:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient leave balance. Available: {available} days, Requested: {days_count} days"
            )
    
    # Create leave request
    new_leave = LeaveDB(
        id=str(uuid.uuid4()),
        employee_id=leave_data.employee_id,
        leave_type=leave_data.leave_type,
        start_date=leave_data.start_date,
        end_date=leave_data.end_date,
        days_count=days_count,
        reason=leave_data.reason,
        attachment_url=leave_data.attachment_url,
        status=LeaveStatus.PENDING
    )
    
    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)
    
    return new_leave

@router.get("")
async def get_leaves(
    page: int = 1,
    limit: int = 10,    
    employee_id: Optional[str] = None,
    status: Optional[LeaveStatus] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",    
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get leave requests with pagination, search, and filters"""
    query = db.query(LeaveDB)

    # Base query with joins
    query = db.query(
        LeaveDB,
        EmployeeDB
    ).join(
        EmployeeDB, LeaveDB.employee_id == EmployeeDB.id
    )    
    
    if employee_id:
        query = query.filter(LeaveDB.employee_id == employee_id)
    if status:
        query = query.filter(LeaveDB.status == status)
    
    leaves = query.order_by(LeaveDB.created_at.desc()).all()

    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_by == "employee_name":
        sort_column = EmployeeDB.name
    elif sort_by == "net_pay":
        sort_column = LeaveDB.leave_type
    elif sort_by == "gross_pay":
        sort_column = LeaveDB.start_date
    elif sort_by == "period_start":
        sort_column = LeaveDB.end_date
    else:
        sort_column = getattr(LeaveDB, sort_by, LeaveDB.created_at)
    
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    skip = (page - 1) * limit
    results = query.offset(skip).limit(limit).all()

    # Format response
    leaves_data = []
    for leave, employee in results:
        leaves_data.append({
            "id": leave.id,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "leave_type": leave.leave_type,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "days_count": leave.days_count,
            "reason": leave.reason,
            "status": leave.status,
            "approved_by": leave.approved_by,
            "created_at": leave.created_at,
        })
    
    return {
        "data": leaves_data,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@router.put("/{leave_id}", response_model=LeaveResponse)
async def update_leave(
    leave_id: str,
    leave_update: LeaveUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Approve/reject leave request"""
    
    leave = db.query(LeaveDB).filter(LeaveDB.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave_update.status == LeaveStatus.APPROVED:
        # Deduct from leave balance
        LeaveCalculator.deduct_leave(
            db, leave.employee_id, leave.leave_type, leave.days_count
        )
        leave.approved_by = current_user.id
        leave.approved_at = datetime.now(timezone.utc)
    
    elif leave_update.status == LeaveStatus.REJECTED:
        leave.rejection_reason = leave_update.rejection_reason
    
    elif leave_update.status == LeaveStatus.CANCELLED:
        # Restore leave balance if it was approved
        if leave.status == LeaveStatus.APPROVED:
            LeaveCalculator.restore_leave(
                db, leave.employee_id, leave.leave_type, leave.days_count
            )
    
    leave.status = leave_update.status
    db.commit()
    db.refresh(leave)
    
    return leave

@router.get("/balance/{employee_id}")
async def get_leave_balance(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get employee leave balance"""
    
    balance = db.query(LeaveBalanceDB).filter(
        LeaveBalanceDB.employee_id == employee_id
    ).first()
    
    if not balance:
        # Initialize balance for new employee
        from datetime import datetime
        balance = LeaveBalanceDB(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            year=datetime.now().year,
            sick_leave_balance=15.0,
            vacation_leave_balance=15.0
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)
    
    return {
        "employee_id": balance.employee_id,
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
    }

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
    assignment: LeaveCreditsAssignment,  # ✅ Now accepts body instead of query params
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Manually assign/adjust leave credits (HR override)"""
    
    balance = db.query(LeaveBalanceDB).filter(
        LeaveBalanceDB.employee_id == assignment.employee_id
    ).first()
    
    if not balance:
        raise HTTPException(status_code=404, detail="Leave balance not found. Initialize first.")
    
    # Apply caps (but allow going below if deducting)
    new_sick = balance.sick_leave_balance + assignment.sick_leave
    new_vacation = balance.vacation_leave_balance + assignment.vacation_leave
    
    # Only apply max cap when adding (allow negative/zero balances for deductions)
    if assignment.sick_leave > 0:
        new_sick = min(new_sick, LeaveCredits.MAX_ACCUMULATED_SICK_LEAVE)
    if assignment.vacation_leave > 0:
        new_vacation = min(new_vacation, LeaveCredits.MAX_ACCUMULATED_VACATION_LEAVE)
    
    old_sick = balance.sick_leave_balance
    old_vacation = balance.vacation_leave_balance
    
    balance.sick_leave_balance = new_sick
    balance.vacation_leave_balance = new_vacation
    
    db.commit()
    db.refresh(balance)
    
    return {
        "message": "Leave credits adjusted",
        "employee_id": assignment.employee_id,
        "changes": {
            "sick_leave": {
                "old": round(old_sick, 1),
                "adjustment": assignment.sick_leave,
                "new": round(new_sick, 1)
            },
            "vacation_leave": {
                "old": round(old_vacation, 1),
                "adjustment": assignment.vacation_leave,
                "new": round(new_vacation, 1)
            }
        },
        "adjusted_by": current_user.email,
        "reason": assignment.reason
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