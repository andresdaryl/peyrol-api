from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import init_db
import logging
from utils.supabase_client import supabase
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded

# Import routers
from routers import auth, account, employees, attendance, payroll, payslips, reports, dashboard, holidays, leaves, company, users, benefits_config, tax_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global rate limiter for demo app (100 requests per minute per IP)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Create FastAPI app
app = FastAPI(
    title="Payroll Management System",
    description="Payroll Management System for micro, small, and medium enterprises. Automate salary calculations, generate payslips, and manage employees — all in one platform.",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

uploads_path = Path("uploads")
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
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

# Logger handler for rate limit events
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    logger.warning(f"Rate limit exceeded for IP: {request.client.host}")
    return _rate_limit_exceeded_handler(request, exc)

@app.get("/")
async def root():
    return {
        "message": "Paymora | Payroll Management System API",
        "version": "1.0.0",
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

@app.get("/ping")
async def ping_supabase():
    try:
        response = supabase.table("heartbeat").select("id").limit(1).execute()
        return {"ok": True, "status": "alive", "count": len(response.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

