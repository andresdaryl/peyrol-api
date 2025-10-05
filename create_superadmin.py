from sqlalchemy.orm import Session
from server import SessionLocal, UserDB, UserRole
import uuid
from datetime import datetime, timezone
import bcrypt

def create_superadmin():
    db = SessionLocal()
    try:
        # Check if superadmin already exists
        existing = db.query(UserDB).filter(UserDB.email == "admin@peyrol.com").first()
        if existing:
            print("Superadmin already exists!")
            print("You can log in with:")
            print("Email: admin@peyrol.com")
            print("Password: admin123")
            return
        
        # Hash password
        password = "admin123"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create superadmin
        superadmin = UserDB(
            id=str(uuid.uuid4()),
            email="admin@peyrol.com",
            name="Super Administrator",
            role=UserRole.SUPERADMIN,
            hashed_password=hashed,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(superadmin)
        db.commit()
        print("✓ Superadmin created successfully!")
        print("Email: admin@peyrol.com")
        print("Password: admin123")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_superadmin()