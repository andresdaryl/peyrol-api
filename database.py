from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database - create all tables"""
    # Import all models to register them with Base
    from models.user import UserDB
    from models.employee import EmployeeDB
    from models.attendance import AttendanceDB
    from models.payroll import PayrollRunDB, PayrollEntryDB, PayslipDB
    from models.benefits import MandatoryContributionsDB
    
    # Create all tables
    Base.metadata.create_all(bind=engine)