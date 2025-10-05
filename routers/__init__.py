"""
Routers package - contains all API route handlers
"""
from routers import auth, account, employees, attendance, payroll, payslips, reports, dashboard

__all__ = [
    'auth',
    'account',
    'employees',
    'attendance',
    'payroll',
    'payslips',
    'reports',
    'dashboard'
]