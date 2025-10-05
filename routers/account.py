from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
from schemas.user import User, UserUpdate, UserPasswordUpdate
from models.user import UserDB
from services.auth import AuthService
from utils.constants import UserRole

router = APIRouter(prefix="/account", tags=["Account Settings"])

@router.get("/me", response_model=User)
async def get_my_account(current_user: User = Depends(get_current_user)):
    """Get current user account information"""
    return current_user

@router.put("/update-profile", response_model=User)
async def update_profile(
    profile_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (name, email)"""
    user_db = db.query(UserDB).filter(UserDB.id == current_user.id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if new email already exists (if email is being changed)
    if profile_update.email and profile_update.email != user_db.email:
        existing_email = db.query(UserDB).filter(
            UserDB.email == profile_update.email,
            UserDB.id != current_user.id
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already in use")
    
    # Update fields
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_db, field, value)
    
    db.commit()
    db.refresh(user_db)
    
    return User(
        id=user_db.id,
        email=user_db.email,
        name=user_db.name,
        role=user_db.role,
        created_at=user_db.created_at
    )

@router.put("/change-password")
async def change_password(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    # Validate new password matches confirmation
    if password_update.new_password != password_update.confirm_password:
        raise HTTPException(
            status_code=400, 
            detail="New password and confirmation do not match"
        )
    
    # Validate password strength (basic check)
    if len(password_update.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )
    
    # Get user from database
    user_db = db.query(UserDB).filter(UserDB.id == current_user.id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not AuthService.verify_password(password_update.current_password, user_db.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect"
        )
    
    # Update password
    user_db.hashed_password = AuthService.get_password_hash(password_update.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.delete("/delete-account")
async def delete_account(
    password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account (requires password confirmation)"""
    # Prevent superadmin from deleting their own account if they're the only one
    if current_user.role == UserRole.SUPERADMIN:
        superadmin_count = db.query(UserDB).filter(
            UserDB.role == UserRole.SUPERADMIN
        ).count()
        if superadmin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last superadmin account"
            )
    
    # Get user from database
    user_db = db.query(UserDB).filter(UserDB.id == current_user.id).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify password
    if not AuthService.verify_password(password, user_db.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Password is incorrect"
        )
    
    # Delete user
    db.delete(user_db)
    db.commit()
    
    return {"message": "Account deleted successfully"}