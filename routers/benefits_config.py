from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from dependencies import get_current_user, require_role
from schemas.user import User
from models.benefits import BenefitsConfigDB
from utils.constants import UserRole
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/benefits-config", tags=["Benefits Configuration"])

class BenefitsConfigCreate(BaseModel):
    benefit_type: str  # 'sss', 'philhealth', 'pagibig'
    year: str
    config_data: dict
    notes: Optional[str] = None

class BenefitsConfigUpdate(BaseModel):
    config_data: Optional[dict] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

@router.get("")
async def get_benefits_configs(
    benefit_type: Optional[str] = None,
    year: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Get all benefits configurations"""
    query = db.query(BenefitsConfigDB)
    
    if benefit_type:
        query = query.filter(BenefitsConfigDB.benefit_type == benefit_type)
    if year:
        query = query.filter(BenefitsConfigDB.year == year)
    if is_active is not None:
        query = query.filter(BenefitsConfigDB.is_active == is_active)
    
    configs = query.order_by(BenefitsConfigDB.year.desc()).all()
    
    return {
        "total": len(configs),
        "data": [
            {
                "id": c.id,
                "benefit_type": c.benefit_type,
                "year": c.year,
                "is_active": c.is_active,
                "config_data": c.config_data,
                "notes": c.notes,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in configs
        ]
    }

@router.get("/{config_id}")
async def get_benefits_config(
    config_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Get benefits configuration by ID"""
    config = db.query(BenefitsConfigDB).filter(BenefitsConfigDB.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    return {
        "id": config.id,
        "benefit_type": config.benefit_type,
        "year": config.year,
        "is_active": config.is_active,
        "config_data": config.config_data,
        "notes": config.notes,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat()
    }

@router.post("")
async def create_benefits_config(
    config_create: BenefitsConfigCreate,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Create new benefits configuration (SuperAdmin only)"""
    
    # Check if config already exists for this type and year
    existing = db.query(BenefitsConfigDB).filter(
        BenefitsConfigDB.benefit_type == config_create.benefit_type,
        BenefitsConfigDB.year == config_create.year
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration for {config_create.benefit_type} year {config_create.year} already exists"
        )
    
    new_config = BenefitsConfigDB(
        id=str(uuid.uuid4()),
        **config_create.dict()
    )
    
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return {
        "message": "Benefits configuration created successfully",
        "config": {
            "id": new_config.id,
            "benefit_type": new_config.benefit_type,
            "year": new_config.year,
            "is_active": new_config.is_active
        }
    }

@router.put("/{config_id}")
async def update_benefits_config(
    config_id: str,
    config_update: BenefitsConfigUpdate,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Update benefits configuration (SuperAdmin only)"""
    config = db.query(BenefitsConfigDB).filter(BenefitsConfigDB.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    update_data = config_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    
    return {
        "message": "Configuration updated successfully",
        "config": {
            "id": config.id,
            "benefit_type": config.benefit_type,
            "year": config.year,
            "is_active": config.is_active
        }
    }

@router.delete("/{config_id}")
async def delete_benefits_config(
    config_id: str,
    current_user: User = Depends(require_role([UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Delete benefits configuration (SuperAdmin only)"""
    config = db.query(BenefitsConfigDB).filter(BenefitsConfigDB.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    
    db.delete(config)
    db.commit()
    
    return {"message": "Configuration deleted successfully"}

@router.get("/preview/{benefit_type}")
async def preview_benefits_calculation(
    benefit_type: str,
    monthly_salary: float,
    year: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.SUPERADMIN])),
    db: Session = Depends(get_db)
):
    """Preview benefits calculation for a given salary"""
    from services.benefits_calculator import BenefitsCalculator
    
    if benefit_type == 'all':
        result = BenefitsCalculator.calculate_all_contributions(monthly_salary, db)
    elif benefit_type == 'sss':
        ee, er = BenefitsCalculator.calculate_sss(monthly_salary, db)
        result = {"employee": ee, "employer": er, "total": ee + er}
    elif benefit_type == 'philhealth':
        ee, er = BenefitsCalculator.calculate_philhealth(monthly_salary, db)
        result = {"employee": ee, "employer": er, "total": ee + er}
    elif benefit_type == 'pagibig':
        ee, er = BenefitsCalculator.calculate_pagibig(monthly_salary, db)
        result = {"employee": ee, "employer": er, "total": ee + er}
    else:
        raise HTTPException(status_code=400, detail="Invalid benefit type")
    
    return {
        "benefit_type": benefit_type,
        "monthly_salary": monthly_salary,
        "calculation": result
    }