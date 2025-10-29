#!/usr/bin/env python3
"""
Database Reset Script for HRIS Application

Usage:
    python scripts/reset_db.py

⚠️  WARNING: This script will DELETE all seeded data from the database!
It includes safety checks and confirmation prompts.

Features:
- Environment check (refuses to run on production)
- Interactive confirmation
- Safe truncation in reverse foreign key order
- Transaction rollback on errors
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal, engine


def is_production() -> bool:
    """
    Check if running in production environment.
    Customize this based on your environment variables.
    """
    env = os.getenv("ENV", "development").lower()
    database_url = os.getenv("DATABASE_URL", "")
    
    # Check for production indicators
    is_prod = (
        env in ["production", "prod"] or
        "prod" in database_url.lower() or
        "production" in database_url.lower()
    )
    
    return is_prod


def confirm_reset() -> bool:
    """Ask for user confirmation before proceeding."""
    print("\n" + "="*60)
    print("⚠️  DATABASE RESET WARNING")
    print("="*60)
    print("\nThis will DELETE all the following data:")
    print("  • Payslips")
    print("  • Mandatory Contributions")
    print("  • Payroll Entries")
    print("  • Payroll Runs")
    print("  • Leave Balances")
    print("  • Leaves")
    print("  • Attendance Records")
    print("  • Holidays")
    print("  • Benefits Configurations")
    print("  • Tax Configurations")
    print("  • Employees")
    print("  • Users")
    print("  • Company Profile")
    print()
    
    response = input("Type 'DELETE ALL DATA' to confirm (or anything else to cancel): ")
    
    return response == "DELETE ALL DATA"


def reset_database():
    """Reset all seeded data from the database."""
    
    # Safety check: refuse to run on production
    if is_production():
        print("\n❌ OPERATION REFUSED")
        print("This appears to be a PRODUCTION environment.")
        print("Database reset is not allowed in production.")
        print("\nIf this is incorrect, check your ENV or DATABASE_URL environment variables.")
        sys.exit(1)
    
    # Get user confirmation
    if not confirm_reset():
        print("\n✋ Operation cancelled by user.")
        print("No data was deleted.")
        sys.exit(0)
    
    print("\n🔄 Starting database reset...")
    
    db = SessionLocal()
    
    try:
        # Delete in reverse order of foreign key dependencies
        tables_to_truncate = [
            ("payslips", "Payslips"),
            ("mandatory_contributions", "Mandatory Contributions"),
            ("payroll_entries", "Payroll Entries"),
            ("payroll_runs", "Payroll Runs"),
            ("leave_balances", "Leave Balances"),
            ("leaves", "Leaves"),
            ("attendance", "Attendance Records"),
            ("holidays", "Holidays"),
            ("benefits_config", "Benefits Configurations"),
            ("tax_config", "Tax Configurations"),
            ("employees", "Employees"),
            ("users", "Users"),
            ("company_profile", "Company Profile"),
        ]
        
        print("\n📋 Deleting data from tables...\n")
        
        for table_name, display_name in tables_to_truncate:
            try:
                # Use DELETE instead of TRUNCATE to respect foreign keys
                result = db.execute(text(f"DELETE FROM {table_name}"))
                db.commit()
                print(f"  ✓ Cleared {display_name} ({result.rowcount} rows)")
            except Exception as e:
                print(f"  ⚠ Could not clear {display_name}: {str(e)}")
                db.rollback()
        
        # Reset sequences (PostgreSQL specific)
        print("\n🔢 Resetting ID sequences...")
        
        sequences = [
            "users",
            "employees",
            "attendance",
            "leaves",
            "leave_balances",
            "holidays",
            "benefits_config",
            "tax_config",
            "payroll_runs",
            "payroll_entries",
            "payslips",
            "mandatory_contributions",
        ]
        
        for table in sequences:
            try:
                # Try to reset sequence if it exists
                db.execute(text(f"ALTER SEQUENCE IF EXISTS {table}_id_seq RESTART WITH 1"))
                db.commit()
            except Exception:
                # Silently ignore if sequence doesn't exist or table doesn't use sequences
                db.rollback()
        
        print("  ✓ Sequences reset\n")
        
        print("="*60)
        print("✅ DATABASE RESET COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nAll seeded data has been removed.")
        print("You can now run the seeder script to populate with fresh data:")
        print("  python scripts/seed_app_data.py")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR during reset: {str(e)}")
        print("🔄 Rolling back transaction...")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        reset_database()
    except KeyboardInterrupt:
        print("\n\n✋ Operation cancelled by user (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error: {str(e)}")
        sys.exit(1)