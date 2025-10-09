from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from utils.constants import UserRole

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: UserRole
    employee_id: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    email: Optional[EmailStr] = None    
    role: Optional[UserRole] = None
    employee_id: Optional[str] = None
    is_active: Optional[bool] = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class User(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    employee_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ResetPasswordRequest(BaseModel):
    new_password: str