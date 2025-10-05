from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from utils.constants import UserRole

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class User(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str