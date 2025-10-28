from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db
import logging

# Import routers
from routers import auth, account, employees, attendance, payroll, payslips, reports, dashboard, holidays, leaves, company, users, benefits_config, tax_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Payroll Management System",
    description="Payroll Management System for micro, small, and medium enterprises. Automate salary calculations, generate payslips, and manage employees — all in one platform.",
    version="1.0.0"
)

uploads_path = Path("uploads")
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(account.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(payroll.router, prefix="/api")
app.include_router(payslips.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(holidays.router, prefix="/api")
app.include_router(leaves.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(benefits_config.router, prefix="/api")
app.include_router(tax_config.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("Application started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Application shutting down")

@app.get("/")
async def root():
    return {
        "message": "Payroll Management System API",
        "version": "2.0.0",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
