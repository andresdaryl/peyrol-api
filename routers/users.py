from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User, UserCreate, UserUpdate, ResetPasswordRequest
from models.user import UserDB
from models.employee import EmployeeDB
from services.auth import AuthService
from utils.constants import UserRole
import uuid

router = APIRouter(prefix="/users", tags=["User Management"])

@router.get("")
async def get_users(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Get all users with pagination and filters (SuperAdmin only)"""
    
    query = db.query(UserDB)
    
    # Apply filters
    if search:
        query = query.filter(
            (UserDB.name.ilike(f"%{search}%")) |
            (UserDB.email.ilike(f"%{search}%"))
        )
    
    if role:
        query = query.filter(UserDB.role == role)
    
    if is_active is not None:
        query = query.filter(UserDB.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    sort_column = getattr(UserDB, sort_by, UserDB.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    skip = (page - 1) * limit
    users = query.offset(skip).limit(limit).all()
    
    # Format response with employee details if applicable
    users_data = []
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "employee_id": user.employee_id,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "employee": None
        }
        
        # If user is an employee, get employee details
        if user.employee_id:
            employee = db.query(EmployeeDB).filter(EmployeeDB.id == user.employee_id).first()
            if employee:
                user_dict["employee"] = {
                    "name": employee.name,
                    "role": employee.role,
                    "department": employee.department,
                    "profile_image_url": employee.profile_image_url
                }
        
        users_data.append(user_dict)
    
    return {
        "data": users_data,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_dict = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "employee_id": user.employee_id,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "employee": None
    }
    
    if user.employee_id:
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == user.employee_id).first()
        if employee:
            user_dict["employee"] = {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "contact": employee.contact,
                "role": employee.role,
                "department": employee.department,
                "profile_image_url": employee.profile_image_url,
                "hire_date": employee.hire_date.isoformat() if employee.hire_date else None
            }
    
    return user_dict

@router.post("", response_model=User)
async def create_user(
    user_create: UserCreate,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Create new user (SuperAdmin only)"""
    
    # Check if email already exists
    existing = db.query(UserDB).filter(UserDB.email == user_create.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # If creating an EMPLOYEE user, validate employee_id
    if user_create.role == UserRole.EMPLOYEE:
        if not user_create.employee_id:
            raise HTTPException(
                status_code=400, 
                detail="employee_id is required for EMPLOYEE role"
            )
        
        # Check if employee exists
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == user_create.employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Check if employee already has a user account
        existing_employee_user = db.query(UserDB).filter(
            UserDB.employee_id == user_create.employee_id
        ).first()
        if existing_employee_user:
            raise HTTPException(
                status_code=400, 
                detail="This employee already has a user account"
            )
    
    # SUPERADMIN can only be created by another SUPERADMIN
    if user_create.role == UserRole.SUPERADMIN:
        if current_user.role != UserRole.SUPERADMIN:
            raise HTTPException(
                status_code=403, 
                detail="Only SuperAdmin can create SuperAdmin users"
            )
    
    # Hash password
    hashed_password = AuthService.get_password_hash(user_create.password)
    
    # Create user
    new_user = UserDB(
        id=str(uuid.uuid4()),
        email=user_create.email,
        name=user_create.name,
        role=user_create.role,
        employee_id=user_create.employee_id,
        hashed_password=hashed_password,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return User(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        employee_id=new_user.employee_id,
        is_active=new_user.is_active,
        created_at=new_user.created_at
    )

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Update user (SuperAdmin only)"""
    
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    
    # Check email uniqueness if changing email
    if 'email' in update_data and update_data['email'] != user.email:
        existing = db.query(UserDB).filter(UserDB.email == update_data['email']).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate employee_id if role is being changed to EMPLOYEE or employee_id is being updated
    if 'role' in update_data and update_data['role'] == UserRole.EMPLOYEE:
        employee_id = update_data.get('employee_id', user.employee_id)
        if not employee_id:
            raise HTTPException(
                status_code=400,
                detail="employee_id is required for EMPLOYEE role"
            )
        
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Check if another user already linked to this employee
        existing_link = db.query(UserDB).filter(
            UserDB.employee_id == employee_id,
            UserDB.id != user_id
        ).first()
        if existing_link:
            raise HTTPException(
                status_code=400,
                detail="This employee is already linked to another user"
            )
    
    # Hash new password if provided
    if 'password' in update_data:
        update_data['hashed_password'] = AuthService.get_password_hash(update_data['password'])
        del update_data['password']
    
    # Update user fields
    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "employee_id": user.employee_id,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat()
    }

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Delete user (SuperAdmin only) - Soft delete by setting is_active to False"""
    
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Prevent deleting the last SuperAdmin
    if user.role == UserRole.SUPERADMIN:
        superadmin_count = db.query(UserDB).filter(
            UserDB.role == UserRole.SUPERADMIN,
            UserDB.is_active == True
        ).count()
        
        if superadmin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last SuperAdmin account"
            )
    
    # Soft delete
    user.is_active = False
    db.commit()
    
    return {"message": "User deactivated successfully"}

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Reactivate a deactivated user"""
    
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    db.commit()
    db.refresh(user)
    
    return {"message": "User activated successfully"}

@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    payload: ResetPasswordRequest,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Reset user password (SuperAdmin only)"""
    
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_password = payload.new_password
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    user.hashed_password = AuthService.get_password_hash(new_password)
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.get("/employees/without-accounts")
async def get_employees_without_accounts(
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Get list of employees who don't have user accounts yet"""
    
    # Get all employee IDs that have user accounts
    employees_with_accounts = db.query(UserDB.employee_id).filter(
        UserDB.employee_id.isnot(None)
    ).all()
    employee_ids_with_accounts = [e[0] for e in employees_with_accounts]
    
    # Get employees without accounts
    employees = db.query(EmployeeDB).filter(
        EmployeeDB.status == "ACTIVE",
        ~EmployeeDB.id.in_(employee_ids_with_accounts)
    ).all()
    
    return {
        "total": len(employees),
        "employees": [
            {
                "id": e.id,
                "name": e.name,
                "email": e.email,
                "role": e.role,
                "department": e.department,
                "profile_image_url": e.profile_image_url
            }
            for e in employees
        ]
    }