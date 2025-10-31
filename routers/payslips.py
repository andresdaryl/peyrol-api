from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from models.payroll import PayrollEntryDB, PayrollRunDB, PayslipDB
from models.employee import EmployeeDB
from models.company import CompanyProfileDB
from services.pdf_generator import PDFGenerator
import uuid
import base64

router = APIRouter(prefix="/payslips", tags=["Payslips"])

@router.get("")
async def get_payslips(
    page: int = 1,
    limit: int = 10,
    employee_id: Optional[str] = None,
    run_id: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payslips with pagination, search, and filters"""
    
    # Base query with joins
    query = db.query(
        PayslipDB,
        PayrollEntryDB,
        PayrollRunDB,
        EmployeeDB
    ).join(
        PayrollEntryDB, PayslipDB.payroll_entry_id == PayrollEntryDB.id
    ).join(
        PayrollRunDB, PayrollEntryDB.payroll_run_id == PayrollRunDB.id
    ).join(
        EmployeeDB, PayslipDB.employee_id == EmployeeDB.id
    )
    
    # Apply filters
    if employee_id:
        query = query.filter(PayslipDB.employee_id == employee_id)
    
    if run_id:
        query = query.filter(PayrollEntryDB.payroll_run_id == run_id)
    
    if search:
        query = query.filter(
            (EmployeeDB.name.ilike(f"%{search}%")) |
            (EmployeeDB.role.ilike(f"%{search}%")) |
            (EmployeeDB.department.ilike(f"%{search}%"))
        )
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_by == "employee_name":
        sort_column = EmployeeDB.name
    elif sort_by == "net_pay":
        sort_column = PayrollEntryDB.net
    elif sort_by == "gross_pay":
        sort_column = PayrollEntryDB.gross
    elif sort_by == "period_start":
        sort_column = PayrollRunDB.start_date
    else:
        sort_column = getattr(PayslipDB, sort_by, PayslipDB.created_at)
    
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    skip = (page - 1) * limit
    results = query.offset(skip).limit(limit).all()
    
    # Format response
    payslips_data = []
    for payslip, entry, run, employee in results:
        payslips_data.append({
            "id": payslip.id,
            "payroll_entry_id": payslip.payroll_entry_id,
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "role": employee.role,
                "department": employee.department,
                "profile_image_url": employee.profile_image_url
            },
            "payroll_run": {
                "id": run.id,
                "type": run.type.value,
                "start_date": run.start_date.isoformat(),
                "end_date": run.end_date.isoformat(),
                "status": run.status.value
            },
            "payroll_entry": {
                "base_pay": entry.base_pay,
                "overtime_pay": entry.overtime_pay,
                "nightshift_pay": entry.nightshift_pay,
                "gross": entry.gross,
                "net": entry.net,
                "is_finalized": entry.is_finalized
            },
            "version": payslip.version,
            "is_editable": payslip.is_editable,
            "created_at": payslip.created_at.isoformat(),
            "has_pdf": payslip.pdf_base64 is not None
        })
    
    return {
        "data": payslips_data,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }

@router.get("/{payslip_id}")
async def get_payslip(
    payslip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed payslip information"""
    
    result = db.query(
        PayslipDB,
        PayrollEntryDB,
        PayrollRunDB,
        EmployeeDB
    ).join(
        PayrollEntryDB, PayslipDB.payroll_entry_id == PayrollEntryDB.id
    ).join(
        PayrollRunDB, PayrollEntryDB.payroll_run_id == PayrollRunDB.id
    ).join(
        EmployeeDB, PayslipDB.employee_id == EmployeeDB.id
    ).filter(
        PayslipDB.id == payslip_id
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Payslip not found")
    
    payslip, entry, run, employee = result
    
    return {
        "id": payslip.id,
        "payroll_entry_id": payslip.payroll_entry_id,
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "contact": employee.contact,
            "role": employee.role,
            "department": employee.department,
            "profile_image_url": employee.profile_image_url,
            "hire_date": employee.hire_date.isoformat() if employee.hire_date else None
        },
        "payroll_run": {
            "id": run.id,
            "type": run.type.value,
            "start_date": run.start_date.isoformat(),
            "end_date": run.end_date.isoformat(),
            "status": run.status.value
        },
        "payroll_entry": {
            "base_pay": entry.base_pay,
            "overtime_pay": entry.overtime_pay,
            "nightshift_pay": entry.nightshift_pay,
            "bonuses": entry.bonuses,
            "benefits": entry.benefits,
            "deductions": entry.deductions,
            "gross": entry.gross,
            "net": entry.net,
            "is_finalized": entry.is_finalized,
            "version": entry.version
        },
        "version": payslip.version,
        "is_editable": payslip.is_editable,
        "created_at": payslip.created_at.isoformat(),
        "has_pdf": payslip.pdf_base64 is not None
    }
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
    
    company = db.query(CompanyProfileDB).first()
    pdf_base64 = PDFGenerator.generate_payslip(entry_dict, employee_dict, run_dict, company_data=company.__dict__)
    
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