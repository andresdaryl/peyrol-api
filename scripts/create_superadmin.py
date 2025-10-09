"""
Run this script once to create the first SuperAdmin user
Usage: python scripts/create_superadmin.py
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models.user import UserDB
from services.auth import AuthService
from utils.constants import UserRole
import uuid

def create_initial_superadmin():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        # Check if any superadmin exists
        existing = db.query(UserDB).filter(UserDB.role == UserRole.SUPERADMIN).first()
        
        if existing:
            print("SuperAdmin already exists!")
            print(f"Email: {existing.email}")
            return
        
        # Create superadmin
        email = input("Enter SuperAdmin email: ")
        name = input("Enter SuperAdmin name: ")
        password = input("Enter SuperAdmin password (min 8 chars): ")
        
        if len(password) < 8:
            print("Password must be at least 8 characters!")
            return
        
        hashed_password = AuthService.get_password_hash(password)
        
        superadmin = UserDB(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            role=UserRole.SUPERADMIN,
            hashed_password=hashed_password,
            is_active=True
        )
        
        db.add(superadmin)
        db.commit()
        
        print("\n✅ SuperAdmin created successfully!")
        print(f"Email: {email}")
        print(f"Name: {name}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_superadmin()