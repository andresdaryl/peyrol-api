from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from schemas.payroll import (
    PayrollRun, PayrollRunCreate, PayrollRunUpdate,
    PayrollEntry, PayrollEntryUpdate
)
from models.payroll import PayrollRunDB, PayrollEntryDB
from models.employee import EmployeeDB
from models.benefits import MandatoryContributionsDB
from services.payroll_calculator import PayrollCalculator
from utils.constants import EmployeeStatus, PayrollRunStatus
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/payroll", tags=["Payroll"])

@router.get("/runs", response_model=List[PayrollRun])
async def get_payroll_runs(
    start_date: Optional[date] = Query(None, description="Filter runs starting on or after this date"),
    end_date: Optional[date] = Query(None, description="Filter runs ending on or before this date"),
    type: Optional[str] = Query(None, description="Filter by payroll run type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all payroll runs with optional filters: start_date, end_date, and type."""
    query = db.query(PayrollRunDB)

    if start_date:
        query = query.filter(PayrollRunDB.start_date >= start_date)
    if end_date:
        query = query.filter(PayrollRunDB.end_date <= end_date)
    if type:
        query = query.filter(PayrollRunDB.type == type)

    runs = query.order_by(PayrollRunDB.created_at.desc()).all()
    return runs

@router.get("/runs/{run_id}", response_model=PayrollRun)
async def get_payroll_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payroll run by ID"""
    run = db.query(PayrollRunDB).filter(PayrollRunDB.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    return run

@router.post("/runs", response_model=PayrollRun)
async def create_payroll_run(
    run_create: PayrollRunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new payroll run"""
    new_run = PayrollRunDB(
        id=str(uuid.uuid4()),
        **run_create.dict()
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    return new_run

@router.put("/runs/{run_id}", response_model=PayrollRun)
async def update_payroll_run(
    run_id: str,
    run_update: PayrollRunUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update payroll run status"""
    run = db.query(PayrollRunDB).filter(PayrollRunDB.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    update_data = run_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(run, field, value)
    
    db.commit()
    db.refresh(run)
    return run

@router.get("/entries", response_model=List[PayrollEntry])
async def get_payroll_entries(
    run_id: Optional[str] = Query(None, description="Filter by payroll run ID"),
    employee_id: Optional[str] = Query(None, description="Filter by employee ID"),
    version: Optional[int] = Query(None, description="Filter by version number"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get payroll entries.
    Optional filters:
    - run_id
    - employee_id
    - version
    """
    query = db.query(PayrollEntryDB)

    if run_id:
        query = query.filter(PayrollEntryDB.payroll_run_id == run_id)

    if employee_id:
        query = query.filter(PayrollEntryDB.employee_id == employee_id)

    if version:
        query = query.filter(PayrollEntryDB.version == version)

    entries = query.order_by(PayrollEntryDB.created_at.desc()).all()
    return entries

@router.get("/entries/{entry_id}", response_model=PayrollEntry)
async def get_payroll_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payroll entry by ID"""
    entry = db.query(PayrollEntryDB).filter(PayrollEntryDB.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    return entry

@router.post("/entries/{run_id}/generate")
async def generate_payroll_entries(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Auto-generate payroll entries with mandatory contributions"""
    run_data = db.query(PayrollRunDB).filter(PayrollRunDB.id == run_id).first()
    if not run_data:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    # Get all active employees
    employees = db.query(EmployeeDB).filter(
        EmployeeDB.status == EmployeeStatus.ACTIVE
    ).all()
    
    generated_entries = []
    for employee in employees:
        # Calculate payroll with mandatory contributions
        calc_result = PayrollCalculator.calculate_for_employee(
            db, employee.id, run_data.start_date, run_data.end_date
        )
        
        if calc_result:
            # Create payroll entry
            new_entry = PayrollEntryDB(
                id=str(uuid.uuid4()),
                payroll_run_id=run_id,
                employee_id=calc_result['employee_id'],
                employee_name=calc_result['employee_name'],
                base_pay=calc_result['base_pay'],
                overtime_pay=calc_result['overtime_pay'],
                nightshift_pay=calc_result['nightshift_pay'],
                bonuses=calc_result['bonuses'],
                benefits=calc_result['benefits'],
                deductions=calc_result['deductions'],
                gross=calc_result['gross'],
                net=calc_result['net']
            )
            db.add(new_entry)
            db.flush()  # Get the entry ID
            
            # Store mandatory contributions separately
            contributions = calc_result['mandatory_contributions']
            mandatory_contrib = MandatoryContributionsDB(
                id=str(uuid.uuid4()),
                employee_id=employee.id,
                payroll_entry_id=new_entry.id,
                sss_employee=contributions['sss']['employee'],
                sss_employer=contributions['sss']['employer'],
                philhealth_employee=contributions['philhealth']['employee'],
                philhealth_employer=contributions['philhealth']['employer'],
                pagibig_employee=contributions['pagibig']['employee'],
                pagibig_employer=contributions['pagibig']['employer'],
                total_employee_contribution=contributions['total_employee'],
                calculation_details={
                    'monthly_salary': calc_result['monthly_salary_equivalent'],
                    'period': f"{run_data.start_date} to {run_data.end_date}"
                }
            )
            db.add(mandatory_contrib)
            generated_entries.append(new_entry)
    
    db.commit()
    
    return {
        "message": f"Generated {len(generated_entries)} payroll entries",
        "count": len(generated_entries),
        "run_id": run_id
    }

@router.put("/entries/{entry_id}", response_model=PayrollEntry)
async def update_payroll_entry(
    entry_id: str,
    entry_update: PayrollEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update payroll entry and recalculate totals"""
    entry = db.query(PayrollEntryDB).filter(PayrollEntryDB.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    
    # Track changes for edit history
    edit_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "edited_by": current_user.email,
        "changes": entry_update.dict(exclude_none=True)
    }
    
    update_data = entry_update.dict(exclude_unset=True)
    
    # Recalculate if financial fields are updated
    if any(k in update_data for k in ["base_pay", "overtime_pay", "nightshift_pay", 
                                       "bonuses", "benefits", "deductions"]):
        base_pay = update_data.get("base_pay", entry.base_pay)
        overtime_pay = update_data.get("overtime_pay", entry.overtime_pay)
        nightshift_pay = update_data.get("nightshift_pay", entry.nightshift_pay)
        bonuses = update_data.get("bonuses", entry.bonuses or {})
        benefits = update_data.get("benefits", entry.benefits or {})
        deductions = update_data.get("deductions", entry.deductions or {})
        
        bonuses_total = sum(bonuses.values()) if bonuses else 0
        benefits_total = sum(benefits.values()) if benefits else 0
        deductions_total = sum(deductions.values()) if deductions else 0
        
        gross = base_pay + overtime_pay + nightshift_pay + bonuses_total + benefits_total
        net = round(gross - deductions_total, 2)
        
        update_data["gross"] = round(gross, 2)
        update_data["net"] = net
    
    # Apply updates
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    # Update version and history
    entry.version += 1
    current_history = entry.edit_history or []
    entry.edit_history = current_history + [edit_record]
    
    db.commit()
    db.refresh(entry)
    return entry

@router.get("/entries/{entry_id}/contributions")
async def get_entry_contributions(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get mandatory contributions for a payroll entry"""
    contrib = db.query(MandatoryContributionsDB).filter(
        MandatoryContributionsDB.payroll_entry_id == entry_id
    ).first()
    
    if not contrib:
        raise HTTPException(status_code=404, detail="Contributions not found")
    
    return {
        "employee_id": contrib.employee_id,
        "payroll_entry_id": contrib.payroll_entry_id,
        "sss": {
            "employee": contrib.sss_employee,
            "employer": contrib.sss_employer,
            "total": contrib.sss_employee + contrib.sss_employer
        },
        "philhealth": {
            "employee": contrib.philhealth_employee,
            "employer": contrib.philhealth_employer,
            "total": contrib.philhealth_employee + contrib.philhealth_employer
        },
        "pagibig": {
            "employee": contrib.pagibig_employee,
            "employer": contrib.pagibig_employer,
            "total": contrib.pagibig_employee + contrib.pagibig_employer
        },
        "total_employee_contribution": contrib.total_employee_contribution,
        "calculation_details": contrib.calculation_details
    }