from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from models.payroll import PayrollEntryDB, PayrollRunDB, PayslipDB
from models.employee import EmployeeDB
from services.pdf_generator import PDFGenerator
import uuid
import base64

router = APIRouter(prefix="/payslips", tags=["Payslips"])

@router.get("")
async def get_payslips(
    employee_id: Optional[str] = None,
    run_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payslips with optional filters"""
    query = db.query(PayslipDB)
    
    if employee_id:
        query = query.filter(PayslipDB.employee_id == employee_id)
    
    if run_id:
        entries = db.query(PayrollEntryDB).filter(
            PayrollEntryDB.payroll_run_id == run_id
        ).all()
        entry_ids = [e.id for e in entries]
        query = query.filter(PayslipDB.payroll_entry_id.in_(entry_ids))
    
    payslips = query.all()
    return payslips

@router.get("/{payslip_id}")
async def get_payslip(
    payslip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payslip by ID"""
    payslip = db.query(PayslipDB).filter(PayslipDB.id == payslip_id).first()
    if not payslip:
        raise HTTPException(status_code=404, detail="Payslip not found")
    return payslip

@router.post("/{entry_id}/generate")
async def generate_payslip(
    entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate payslip PDF for a payroll entry"""
    entry = db.query(PayrollEntryDB).filter(PayrollEntryDB.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Payroll entry not found")
    
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == entry.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    run = db.query(PayrollRunDB).filter(PayrollRunDB.id == entry.payroll_run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    entry_dict = {
        "base_pay": entry.base_pay,
        "overtime_pay": entry.overtime_pay,
        "nightshift_pay": entry.nightshift_pay,
        "bonuses": entry.bonuses,
        "benefits": entry.benefits,
        "deductions": entry.deductions,
        "gross": entry.gross,
        "net": entry.net
    }
    
    employee_dict = {
        "id": employee.id,
        "name": employee.name,
        "role": employee.role
    }
    
    run_dict = {
        "start_date": run.start_date.isoformat(),
        "end_date": run.end_date.isoformat(),
        "type": run.type.value
    }
    
    pdf_base64 = PDFGenerator.generate_payslip(entry_dict, employee_dict, run_dict)
    
    existing = db.query(PayslipDB).filter(PayslipDB.payroll_entry_id == entry_id).first()
    
    if existing:
        existing.pdf_base64 = pdf_base64
        existing.version += 1
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_payslip = PayslipDB(
            id=str(uuid.uuid4()),
            payroll_entry_id=entry_id,
            employee_id=entry.employee_id,
            pdf_base64=pdf_base64
        )
        db.add(new_payslip)
        db.commit()
        db.refresh(new_payslip)
        return new_payslip

@router.get("/{payslip_id}/download")
async def download_payslip(
    payslip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download payslip PDF"""
    payslip = db.query(PayslipDB).filter(PayslipDB.id == payslip_id).first()
    if not payslip or not payslip.pdf_base64:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    pdf_bytes = base64.b64decode(payslip.pdf_base64)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payslip_{payslip_id}.pdf"}
    )