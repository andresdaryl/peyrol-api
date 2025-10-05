from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

class Settings:
    # Database
    DATABASE_URL: str = os.environ.get(
        'DATABASE_URL', 
        'postgresql://postgres:postgres@localhost:5432/payroll_db'
    )
    
    # Security
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", 
        "your-secret-key-change-in-production"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    CORS_ORIGINS: list = os.environ.get('CORS_ORIGINS', '*').split(',')

settings = Settings()