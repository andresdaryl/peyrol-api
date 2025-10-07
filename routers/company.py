from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User
from models.company import CompanyProfileDB
from utils.constants import UserRole
from pydantic import BaseModel, EmailStr
from pathlib import Path
import shutil
from typing import Optional

router = APIRouter(prefix="/company", tags=["Company"])

LOGO_DIR = Path("uploads/company")
LOGO_DIR.mkdir(parents=True, exist_ok=True)

class CompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    address: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[EmailStr] = None
    tax_id: Optional[str] = None

@router.get("/profile")
async def get_company_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get company profile"""
    profile = db.query(CompanyProfileDB).first()
    if not profile:
        # Create default profile if doesn't exist
        profile = CompanyProfileDB(
            id="company_001",
            company_name="Your Company Name"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    return profile

@router.put("/profile")
async def update_company_profile(
    profile_update: CompanyProfileUpdate,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Update company profile (Admin/SuperAdmin only)"""
    profile = db.query(CompanyProfileDB).first()
    
    if not profile:
        profile = CompanyProfileDB(id="company_001")
        db.add(profile)
    
    update_data = profile_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile

@router.post("/logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Upload company logo"""
    
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are allowed")
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    profile = db.query(CompanyProfileDB).first()
    if not profile:
        profile = CompanyProfileDB(id="company_001", company_name="Your Company")
        db.add(profile)
    
    # Delete old logo if exists
    if profile.logo_url:
        old_path = Path(profile.logo_url)
        if old_path.exists():
            old_path.unlink()
    
    # Save new logo
    file_extension = file.filename.split(".")[-1]
    new_filename = f"company_logo.{file_extension}"
    file_path = LOGO_DIR / new_filename
    
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    profile.logo_url = str(file_path)
    db.commit()
    db.refresh(profile)
    
    return {
        "message": "Company logo uploaded successfully",
        "logo_url": str(file_path)
    }

@router.delete("/logo")
async def delete_company_logo(
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Delete company logo"""
    profile = db.query(CompanyProfileDB).first()
    if not profile or not profile.logo_url:
        raise HTTPException(status_code=404, detail="Logo not found")
    
    file_path = Path(profile.logo_url)
    if file_path.exists():
        file_path.unlink()
    
    profile.logo_url = None
    db.commit()
    
    return {"message": "Logo deleted successfully"}