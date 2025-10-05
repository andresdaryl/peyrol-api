"""
Routers package - contains all API route handlers
"""
from routers import auth, account, employees, attendance, payroll, payslips, reports, dashboard, leaves, holidays

__all__ = [
    'auth',
    'account',
    'employees',
    'attendance',
    'payroll',
    'payslips',
    'reports',
    'dashboard',
    'leaves',
    'holidays'
]