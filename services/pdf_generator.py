import io
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

pdfmetrics.registerFont(TTFont('DejaVuSans', 'fonts/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'fonts/DejaVuSans-Bold.ttf'))

class PDFGenerator:
    """Generate enhanced payslip PDFs with detailed breakdowns."""
    
    @staticmethod
    def generate_payslip(
        entry_data: Dict[str, Any], 
        employee_data: Dict[str, Any], 
        payroll_run_data: Dict[str, Any],
        company_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate comprehensive payslip PDF with all earnings, detailed deductions, and attendance summary."""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()

        company_name = company_data.get("company_name", "Your Company Name") if company_data else "Your Company Name"
        logo_url = company_data.get("logo_url") if company_data else None
        page_width, page_height = letter
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#d97706'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='DejaVuSans-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        elements.append(Paragraph("PAYSLIP", title_style))
        elements.append(Paragraph(company_name, subtitle_style))
        elements.append(Spacer(1, 0.15*inch))

        logo_path = None
        if company_data and company_data.get("logo_url"):
            candidate = Path(company_data["logo_url"])
            if candidate.exists():
                logo_path = str(candidate)
            else:
                logo_path = None

        def draw_logo_on_first_page(canvas, doc):
            if not logo_path:
                return
            try:
                logo_w = 0.75 * inch
                logo_h = 0.75 * inch

                left_margin = doc.leftMargin if getattr(doc, "leftMargin", None) is not None else 0.5 * inch
                x = left_margin

                top_margin = doc.topMargin if getattr(doc, "topMargin", None) is not None else 0.5 * inch
                y = page_height - top_margin - (logo_h / 2)

                canvas.drawImage(logo_path, x, y - logo_h/2, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass        
        
        info_data = [
            ['Employee:', employee_data['name'], 'Period:', f"{payroll_run_data['start_date']} to {payroll_run_data['end_date']}"],
            ['Employee ID:', employee_data['id'][:8], 'Pay Type:', payroll_run_data['type'].upper()],
            ['Role:', employee_data['role'], 'Generated:', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')],
        ]
        
        info_table = Table(info_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'DejaVuSans-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#374151')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.25*inch))
        
        if 'attendance_summary' in entry_data:
            att_sum = entry_data['attendance_summary']
            status_br = att_sum.get('status_breakdown', {})
            
            att_data = [
                ['ATTENDANCE SUMMARY', '', ''],
                ['Total Days:', str(att_sum.get('total_days', 0)), ''],
                ['Present:', str(status_br.get('present', 0)), ''],
                ['Late:', str(status_br.get('late', 0)), ''],
                ['Absent:', str(status_br.get('absent', 0)), ''],
                ['Undertime:', str(status_br.get('undertime', 0)), ''],
                ['On Leave:', str(status_br.get('on_leave', 0)), ''],
            ]
            
            att_table = Table(att_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
            att_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('FONTNAME', (0, 1), (-1, -1), 'DejaVuSans'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(att_table)
            elements.append(Spacer(1, 0.2*inch))
        
        earnings_data = [
            ['EARNINGS', '', 'AMOUNT'],
            ['Base Pay', '', f"{entry_data['base_pay']:,.2f}"],
            ['Overtime Pay', '', f"{entry_data.get('overtime_pay', 0):,.2f}"],
            ['Night Shift Pay', '', f"{entry_data.get('nightshift_pay', 0):,.2f}"],
        ]
        
        if entry_data.get('holiday_premium_pay', 0) > 0:
            earnings_data.append(['Holiday Premium', '', f"{entry_data['holiday_premium_pay']:,.2f}"])
        if entry_data.get('holiday_overtime_pay', 0) > 0:
            earnings_data.append(['Holiday Overtime', '', f"{entry_data['holiday_overtime_pay']:,.2f}"])
        
        if entry_data.get('benefits'):
            for benefit, amount in entry_data['benefits'].items():
                earnings_data.append([benefit.replace('_', ' ').title(), '', f"{amount:,.2f}"])
        
        if entry_data.get('bonuses'):
            for bonus, amount in entry_data['bonuses'].items():
                earnings_data.append([bonus.replace('_', ' ').title(), '', f"{amount:,.2f}"])
        
        earnings_data.append(['', 'GROSS PAY:', f"₱{entry_data['gross']:,.2f}"])
        
        earnings_table = Table(earnings_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        earnings_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (1, -1), (-1, -1), 'DejaVuSans-Bold'),
            ('FONTSIZE', (1, -1), (-1, -1), 11),
            ('BACKGROUND', (1, -1), (-1, -1), colors.HexColor('#fef3c7')),
            ('LINEABOVE', (1, -1), (-1, -1), 2, colors.HexColor('#f59e0b')),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(earnings_table)
        elements.append(Spacer(1, 0.2*inch))
        
        deductions_data = [['DEDUCTIONS', '', 'AMOUNT']]
        
        deductions_data.append(['SSS Contribution', '', f"{entry_data.get('deductions', {}).get('sss', 0):,.2f}"])
        deductions_data.append(['PhilHealth Contribution', '', f"{entry_data.get('deductions', {}).get('philhealth', 0):,.2f}"])
        deductions_data.append(['Pag-IBIG Contribution', '', f"{entry_data.get('deductions', {}).get('pagibig', 0):,.2f}"])
        
        late_ded = entry_data.get('deductions', {}).get('late', 0)
        absent_ded = entry_data.get('deductions', {}).get('absent', 0)
        undertime_ded = entry_data.get('deductions', {}).get('undertime', 0)
        
        if late_ded > 0:
            deductions_data.append(['Late Deduction', '', f"{late_ded:,.2f}"])
        if absent_ded > 0:
            deductions_data.append(['Absent Deduction', '', f"{absent_ded:,.2f}"])
        if undertime_ded > 0:
            deductions_data.append(['Undertime Deduction', '', f"{undertime_ded:,.2f}"])
        
        if entry_data.get('deductions'):
            EXCLUDED_DEDUCTIONS = ['sss', 'philhealth', 'pagibig', 'late', 'absent', 'undertime']
            for deduction, amount in entry_data['deductions'].items():
                if deduction not in EXCLUDED_DEDUCTIONS:
                    deductions_data.append([deduction.replace('_', ' ').title(), '', f"{amount:,.2f}"])
        
        total_deductions = sum((entry_data.get('deductions') or {}).values())
        deductions_data.append(['', 'TOTAL DEDUCTIONS:', f"₱{total_deductions:,.2f}"])
        
        deductions_table = Table(deductions_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
        deductions_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (1, -1), (-1, -1), 'DejaVuSans-Bold'),
            ('FONTSIZE', (1, -1), (-1, -1), 11),
            ('BACKGROUND', (1, -1), (-1, -1), colors.HexColor('#fee2e2')),
            ('LINEABOVE', (1, -1), (-1, -1), 2, colors.HexColor('#ef4444')),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(deductions_table)
        elements.append(Spacer(1, 0.3*inch))
        
        net_data = [['NET PAY', f"₱{entry_data['net']:,.2f}"]]
        net_table = Table(net_data, colWidths=[4.5*inch, 1.5*inch])
        net_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 18), # Used 18 (larger)
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#14b8a6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(net_table)
        
        elements.append(Spacer(1, 0.4*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(
            "This is a computer-generated payslip and does not require a signature.<br/>For inquiries, contact HR Department.", 
            footer_style
        ))
        
        # Build PDF
        doc.build(elements, onFirstPage=draw_logo_on_first_page)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(pdf_bytes).decode('utf-8')