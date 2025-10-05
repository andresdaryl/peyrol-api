from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import UserDB
from schemas.user import User
from services.auth import AuthService
from utils.constants import UserRole

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    email = AuthService.verify_token(credentials.credentials)
    
    user_data = db.query(UserDB).filter(UserDB.email == email).first()
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return User(
        id=user_data.id,
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        created_at=user_data.created_at
    )

def require_role(required_roles: List[UserRole]):
    """Dependency to check if user has required role"""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker