import io
import base64
from datetime import datetime, timezone
from typing import Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('DejaVuSans', 'fonts/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'fonts/DejaVuSans-Bold.ttf'))

class PDFGenerator:
    """Generate enhanced payslip PDFs with detailed breakdowns"""
    
    @staticmethod
    def generate_payslip(
        entry_data: Dict[str, Any], 
        employee_data: Dict[str, Any], 
        payroll_run_data: Dict[str, Any]
    ) -> str:
        """Generate comprehensive payslip PDF with all deductions and premiums"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#d97706'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # Title
        elements.append(Paragraph("PAYSLIP", title_style))
        elements.append(Paragraph("Construction Company Payroll System", subtitle_style))
        
        # Employee Info Section
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
        
        # Attendance Summary (if available)
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
        
        # Earnings Table
        earnings_data = [
            ['EARNINGS', '', 'AMOUNT'],
            ['Base Pay', '', f"₱{entry_data['base_pay']:,.2f}"],
            ['Overtime Pay', '', f"₱{entry_data.get('overtime_pay', 0):,.2f}"],
            ['Night Shift Pay', '', f"₱{entry_data.get('nightshift_pay', 0):,.2f}"],
        ]
        
        # Add holiday premiums if present
        if entry_data.get('holiday_premium_pay', 0) > 0:
            earnings_data.append(['Holiday Premium', '', f"₱{entry_data['holiday_premium_pay']:,.2f}"])
        if entry_data.get('holiday_overtime_pay', 0) > 0:
            earnings_data.append(['Holiday Overtime', '', f"₱{entry_data['holiday_overtime_pay']:,.2f}"])
        
        # Add benefits
        if entry_data.get('benefits'):
            for benefit, amount in entry_data['benefits'].items():
                earnings_data.append([benefit.replace('_', ' ').title(), '', f"₱{amount:,.2f}"])
        
        # Add bonuses
        if entry_data.get('bonuses'):
            for bonus, amount in entry_data['bonuses'].items():
                earnings_data.append([bonus.replace('_', ' ').title(), '', f"₱{amount:,.2f}"])
        
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
        
        # Deductions Table (Enhanced)
        deductions_data = [['DEDUCTIONS', '', 'AMOUNT']]
        
        # Mandatory contributions
        deductions_data.append(['SSS Contribution', '', f"₱{entry_data.get('deductions', {}).get('sss', 0):,.2f}"])
        deductions_data.append(['PhilHealth Contribution', '', f"₱{entry_data.get('deductions', {}).get('philhealth', 0):,.2f}"])
        deductions_data.append(['Pag-IBIG Contribution', '', f"₱{entry_data.get('deductions', {}).get('pagibig', 0):,.2f}"])
        
        # Attendance deductions (NEW)
        late_ded = entry_data.get('deductions', {}).get('late', 0)
        absent_ded = entry_data.get('deductions', {}).get('absent', 0)
        undertime_ded = entry_data.get('deductions', {}).get('undertime', 0)
        
        if late_ded > 0:
            deductions_data.append(['Late Deduction', '', f"₱{late_ded:,.2f}"])
        if absent_ded > 0:
            deductions_data.append(['Absent Deduction', '', f"₱{absent_ded:,.2f}"])
        if undertime_ded > 0:
            deductions_data.append(['Undertime Deduction', '', f"₱{undertime_ded:,.2f}"])
        
        # Other deductions
        if entry_data.get('deductions'):
            for deduction, amount in entry_data['deductions'].items():
                if deduction not in ['sss', 'philhealth', 'pagibig', 'late', 'absent', 'undertime']:
                    deductions_data.append([deduction.replace('_', ' ').title(), '', f"₱{amount:,.2f}"])
        
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
        
        # Net Pay
        net_data = [['NET PAY', f"₱{entry_data['net']:,.2f}"]]
        net_table = Table(net_data, colWidths=[4.5*inch, 1.5*inch])
        net_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 18),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#14b8a6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(net_table)
        
        # Footer with disclaimer
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
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(pdf_bytes).decode('utf-8')
    """Generate payslip PDFs"""
    
    @staticmethod
    def generate_payslip(
        entry_data: Dict[str, Any], 
        employee_data: Dict[str, Any], 
        payroll_run_data: Dict[str, Any]
    ) -> str:
        """Generate a professional payslip PDF with mandatory contributions"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#d97706'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Title
        elements.append(Paragraph("PAYSLIP", title_style))
        elements.append(Paragraph("MSME Payroll", subtitle_style))
        
        # Employee Info
        info_data = [
            ['Employee:', employee_data['name'], 'Period:', f"{payroll_run_data['start_date']} to {payroll_run_data['end_date']}"],
            ['Employee ID:', employee_data['id'][:8], 'Payroll Type:', payroll_run_data['type']],
            ['Role:', employee_data['role'], 'Generated:', datetime.now(timezone.utc).strftime('%Y-%m-%d')],
        ]
        
        info_table = Table(info_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'DejaVuSans-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'DejaVuSans-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Earnings Table
        earnings_data = [
            ['EARNINGS', '', 'AMOUNT'],
            ['Base Pay', '', f"₱{entry_data['base_pay']:,.2f}"],
            ['Overtime Pay', '', f"{entry_data['overtime_pay']:,.2f}"],
            ['Night Shift Pay', '', f"{entry_data['nightshift_pay']:,.2f}"],
        ]
        
        if entry_data.get('benefits'):
            for benefit, amount in entry_data['benefits'].items():
                earnings_data.append([benefit.replace('_', ' ').title(), '', f"₱{amount:,.2f}"])
        
        if entry_data.get('bonuses'):
            for bonus, amount in entry_data['bonuses'].items():
                earnings_data.append([bonus.replace('_', ' ').title(), '', f"₱{amount:,.2f}"])
        
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
        
        # Deductions Table (with mandatory contributions)
        deductions_data = [['DEDUCTIONS', '', 'AMOUNT']]
        
        # Mandatory contributions section
        deductions_data.append(['SSS Contribution', '', f"₱{entry_data.get('deductions', {}).get('sss', 0):,.2f}"])
        deductions_data.append(['PhilHealth Contribution', '', f"{entry_data.get('deductions', {}).get('philhealth', 0):,.2f}"])
        deductions_data.append(['Pag-IBIG Contribution', '', f"{entry_data.get('deductions', {}).get('pagibig', 0):,.2f}"])
        
        # Other deductions
        if entry_data.get('deductions'):
            for deduction, amount in entry_data['deductions'].items():
                if deduction not in ['sss', 'philhealth', 'pagibig']:
                    deductions_data.append([deduction.replace('_', ' ').title(), '', f"₱{amount:,.2f}"])
        
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
        
        # Net Pay
        net_data = [['NET PAY', f"₱{entry_data['net']:,.2f}"]]
        net_table = Table(net_data, colWidths=[4.5*inch, 1.5*inch])
        net_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'DejaVuSans-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 16),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#14b8a6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        elements.append(net_table)
        
        # Footer
        elements.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(
            "This is a computer-generated payslip and does not require a signature.", 
            footer_style
        ))
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return base64.b64encode(pdf_bytes).decode('utf-8')