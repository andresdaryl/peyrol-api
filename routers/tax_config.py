from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User
from models.taxes import TaxConfigDB
from utils.constants import UserRole
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/tax-config", tags=["Tax Configuration"])

class TaxConfigCreate(BaseModel):
    tax_type: str  # 'withholding_tax', 'percentage_tax'
    year: str
    tax_brackets: list
    notes: Optional[str] = None

class TaxConfigUpdate(BaseModel):
    tax_brackets: Optional[list] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("")
async def get_tax_configs(
    tax_type: Optional[str] = None,
    year: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Get all tax configurations"""
    query = db.query(TaxConfigDB)
    
    if tax_type:
        query = query.filter(TaxConfigDB.tax_type == tax_type)
    if year:
        query = query.filter(TaxConfigDB.year == year)
    if is_active is not None:
        query = query.filter(TaxConfigDB.is_active == is_active)
    
    configs = query.order_by(TaxConfigDB.year.desc()).all()
    
    return {
        "total": len(configs),
        "data": [
            {
                "id": c.id,
                "tax_type": c.tax_type,
                "year": c.year,
                "is_active": c.is_active,
                "tax_brackets": c.tax_brackets,
                "notes": c.notes,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in configs
        ]
    }

@router.post("")
async def create_tax_config(
    config_create: TaxConfigCreate,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Create new tax configuration (SuperAdmin only)"""
    
    # Check if config already exists
    existing = db.query(TaxConfigDB).filter(
        TaxConfigDB.tax_type == config_create.tax_type,
        TaxConfigDB.year == config_create.year
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Tax configuration for {config_create.tax_type} year {config_create.year} already exists"
        )
    
    new_config = TaxConfigDB(
        id=str(uuid.uuid4()),
        **config_create.dict()
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return {
        "message": "Tax configuration created successfully",
        "config": {
            "id": new_config.id,
            "tax_type": new_config.tax_type,
            "year": new_config.year
        }
    }

@router.put("/{config_id}")
async def update_tax_config(
    config_id: str,
    config_update: TaxConfigUpdate,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Update tax configuration (SuperAdmin only)"""
    config = db.query(TaxConfigDB).filter(TaxConfigDB.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    update_data = config_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return {"message": "Tax configuration updated successfully"}

@router.get("/preview")
async def preview_tax_calculation(
    annual_income: float,
    year: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Preview tax calculation for a given annual income"""
    from services.tax_calculator import TaxCalculator
    
    annual_tax = TaxCalculator.calculate_annual_tax(annual_income, db)
    monthly_tax = annual_tax / 12
    
    return {
        "annual_income": annual_income,
        "annual_tax": round(annual_tax, 2),
        "monthly_tax": round(monthly_tax, 2),
        "effective_rate": round((annual_tax / annual_income * 100), 2) if annual_income > 0 else 0
    }