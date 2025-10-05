from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
from schemas.user import User
from models.payroll import PayrollEntryDB, PayrollRunDB
from models.benefits import MandatoryContributionsDB

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/payroll-summary/{run_id}")
async def get_payroll_summary(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive summary of payroll run including contributions"""
    entries = db.query(PayrollEntryDB).filter(
        PayrollEntryDB.payroll_run_id == run_id
    ).all()
    
    if not entries:
        return {"message": "No payroll entries found", "summary": {}}
    
    contributions = db.query(MandatoryContributionsDB).filter(
        MandatoryContributionsDB.payroll_entry_id.in_([e.id for e in entries])
    ).all()
    
    total_base_pay = sum(e.base_pay for e in entries)
    total_overtime = sum(e.overtime_pay for e in entries)
    total_nightshift = sum(e.nightshift_pay for e in entries)
    total_gross = sum(e.gross for e in entries)
    total_deductions = sum(sum((e.deductions or {}).values()) for e in entries)
    total_net = sum(e.net for e in entries)
    
    # Contributions summary
    total_sss_ee = sum(c.sss_employee for c in contributions)
    total_sss_er = sum(c.sss_employer for c in contributions)
    total_philhealth_ee = sum(c.philhealth_employee for c in contributions)
    total_philhealth_er = sum(c.philhealth_employer for c in contributions)
    total_pagibig_ee = sum(c.pagibig_employee for c in contributions)
    total_pagibig_er = sum(c.pagibig_employer for c in contributions)
    
    return {
        "run_id": run_id,
        "total_employees": len(entries),
        "summary": {
            "total_base_pay": round(total_base_pay, 2),
            "total_overtime_pay": round(total_overtime, 2),
            "total_nightshift_pay": round(total_nightshift, 2),
            "total_gross": round(total_gross, 2),
            "total_deductions": round(total_deductions, 2),
            "total_net": round(total_net, 2)
        },
        "mandatory_contributions": {
            "sss": {
                "employee": round(total_sss_ee, 2),
                "employer": round(total_sss_er, 2),
                "total": round(total_sss_ee + total_sss_er, 2)
            },
            "philhealth": {
                "employee": round(total_philhealth_ee, 2),
                "employer": round(total_philhealth_er, 2),
                "total": round(total_philhealth_ee + total_philhealth_er, 2)
            },
            "pagibig": {
                "employee": round(total_pagibig_ee, 2),
                "employer": round(total_pagibig_er, 2),
                "total": round(total_pagibig_ee + total_pagibig_er, 2)
            },
            "grand_total": {
                "employee": round(total_sss_ee + total_philhealth_ee + total_pagibig_ee, 2),
                "employer": round(total_sss_er + total_philhealth_er + total_pagibig_er, 2),
                "combined": round(total_sss_ee + total_sss_er + total_philhealth_ee + 
                                total_philhealth_er + total_pagibig_ee + total_pagibig_er, 2)
            }
        }
    }

@router.get("/employee-history/{employee_id}")
async def get_employee_payroll_history(
    employee_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payroll history for an employee"""
    entries = db.query(PayrollEntryDB).filter(
        PayrollEntryDB.employee_id == employee_id
    ).order_by(PayrollEntryDB.created_at.desc()).all()
    
    history = []
    for entry in entries:
        run = db.query(PayrollRunDB).filter(PayrollRunDB.id == entry.payroll_run_id).first()
        
        # Get contributions for this entry
        contrib = db.query(MandatoryContributionsDB).filter(
            MandatoryContributionsDB.payroll_entry_id == entry.id
        ).first()
        
        history_item = {
            "payroll_run_id": entry.payroll_run_id,
            "period": f"{run.start_date} to {run.end_date}" if run else "Unknown",
            "gross": entry.gross,
            "net": entry.net,
            "created_at": entry.created_at
        }
        
        if contrib:
            history_item["contributions"] = {
                "sss": contrib.sss_employee,
                "philhealth": contrib.philhealth_employee,
                "pagibig": contrib.pagibig_employee,
                "total": contrib.total_employee_contribution
            }
        
        history.append(history_item)
    
    return {
        "employee_id": employee_id,
        "total_payrolls": len(history),
        "history": history
    }

@router.get("/contributions-remittance/{run_id}")
async def get_contributions_remittance(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get remittance summary for government contributions"""
    entries = db.query(PayrollEntryDB).filter(
        PayrollEntryDB.payroll_run_id == run_id
    ).all()
    
    if not entries:
        raise HTTPException(status_code=404, detail="No entries found for this payroll run")
    
    contributions = db.query(MandatoryContributionsDB).filter(
        MandatoryContributionsDB.payroll_entry_id.in_([e.id for e in entries])
    ).all()
    
    # Build employee-level breakdown
    employee_breakdown = []
    for contrib in contributions:
        employee = db.query(EmployeeDB).filter(EmployeeDB.id == contrib.employee_id).first()
        if employee:
            employee_breakdown.append({
                "employee_id": employee.id,
                "employee_name": employee.name,
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
                }
            })
    
    # Calculate totals
    total_sss = sum(c.sss_employee + c.sss_employer for c in contributions)
    total_philhealth = sum(c.philhealth_employee + c.philhealth_employer for c in contributions)
    total_pagibig = sum(c.pagibig_employee + c.pagibig_employer for c in contributions)
    
    return {
        "run_id": run_id,
        "total_employees": len(contributions),
        "remittance_summary": {
            "sss": {
                "total_amount": round(total_sss, 2),
                "due_date": "Last day of the month following the applicable month"
            },
            "philhealth": {
                "total_amount": round(total_philhealth, 2),
                "due_date": "Last day of the month following the applicable month"
            },
            "pagibig": {
                "total_amount": round(total_pagibig, 2),
                "due_date": "Last day of the month following the applicable month"
            },
            "grand_total": round(total_sss + total_philhealth + total_pagibig, 2)
        },
        "employee_breakdown": employee_breakdown
    }