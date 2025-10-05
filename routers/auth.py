from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User, UserCreate, UserLogin, Token
from models.user import UserDB
from services.auth import AuthService
from utils.constants import UserRole
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User)
async def register_user(
    user_create: UserCreate,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """SuperAdmin can create new Admin or SuperAdmin users"""
    existing = db.query(UserDB).filter(UserDB.email == user_create.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = AuthService.get_password_hash(user_create.password)
    
    new_user = UserDB(
        id=str(uuid.uuid4()),
        email=user_create.email,
        name=user_create.name,
        role=user_create.role,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return User(
        id=new_user.id,
        email=new_user.email,
        name=new_user.name,
        role=new_user.role,
        created_at=new_user.created_at
    )

@router.post("/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token"""
    user_data = db.query(UserDB).filter(UserDB.email == user_login.email).first()
    if not user_data or not AuthService.verify_password(user_login.password, user_data.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = AuthService.create_access_token(data={"sub": user_data.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user