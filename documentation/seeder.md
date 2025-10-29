# Database Seeder Scripts

## Overview

These scripts populate your HRIS database with realistic mock data for testing and development purposes. They are **idempotent** (safe to run multiple times) and include safety checks for production environments.

## Files

- **`scripts/seed_app_data.py`** — Seeds the database with comprehensive mock data
- **`scripts/reset_db.py`** — Safely deletes all seeded data (with confirmations)

---

## Quick Start

### Basic Usage

```bash
# Seed the database with mock data
python scripts/seed_app_data.py

# Reset and reseed (fresh data)
python scripts/reset_db.py && python scripts/seed_app_data.py

# Use a fixed random seed for reproducible data
python scripts/seed_app_data.py --seed 42
```

---

## What Gets Seeded

### 👥 Users (3)

- 1 SuperAdmin: `superadmin@company.com` / `superadmin123`
- 2 Admins: `admin1@company.com` / `admin123`, `admin2@company.com` / `admin123`

### 🧍 Employees (8)

- Diverse roles: Software Engineers, HR Manager, Accountant, Project Manager, etc.
- Various departments: Engineering, HR, Finance, Marketing, Creative, Operations
- Mixed salary types: Monthly and Daily
- Realistic allowances, benefits, and JSON data

### ⏰ Attendance (~80 records)

- ~10 attendance records per employee
- Last 14 days (working days only)
- Mix of statuses: Present (75%), Late (10%), Undertime (5%), Absent (10%)
- Includes overtime hours, deductions, and holiday flags

### 🌴 Leave Management

- 5-10 leave requests across employees
- Types: Sick, Vacation, Emergency, Maternity, Paternity
- Mix of pending and approved statuses
- Leave balances for all employees (current year)

### 📅 Holidays (5)

- Philippine national holidays
- New Year's Day, Labor Day, Independence Day, Bonifacio Day, Christmas
- Marked as recurring

### 💰 Payroll

- 1 PayrollRun for the last pay period (semi-monthly)
- PayrollEntries for all employees with:
  - Base pay, overtime, night shift pay
  - Allowances and bonuses
  - Benefits deductions (SSS, PhilHealth, Pag-IBIG)
  - Withholding tax calculations
  - Late/absent deductions
- Payslips for each entry
- MandatoryContributions records with employer/employee shares

### ⚙️ Configuration

- BenefitsConfig: SSS, PhilHealth, Pag-IBIG rates
- TaxConfig: Philippine withholding tax brackets
- CompanyProfile: Single company record

---

## Safety Features

### Idempotency

- Checks for existing special records (SuperAdmin, company profile, configs)
- Skips duplicates based on unique constraints (emails, dates, etc.)
- Safe to run multiple times without creating duplicates

### Production Protection

`reset_db.py` includes multiple safety checks:

- Refuses to run if `ENV=production` or `ENV=prod`
- Refuses if `DATABASE_URL` contains "prod" or "production"
- Requires typing "DELETE ALL DATA" to confirm

### Transaction Safety

- All operations wrapped in database transactions
- Automatic rollback on errors
- Clear error messages and stack traces

---

## Advanced Usage

### Custom Random Seed

```bash
# Generate reproducible data (same data every time)
python scripts/seed_app_data.py --seed 12345
```

### Reset Specific Tables

If you need to manually reset specific tables, you can modify `reset_db.py` or use psql:

```sql
-- Delete specific table data
DELETE FROM attendance WHERE date >= '2024-01-01';
DELETE FROM leaves WHERE status = 'PENDING';
```

### Environment Variables

The scripts use your existing database configuration from `app/core/database.py`.

Ensure these are set:

- `DATABASE_URL` — PostgreSQL connection string
- `ENV` — Environment name (development, staging, production)

---

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solution:** Run from project root, not from `scripts/` directory

```bash
# ❌ Wrong (from scripts directory)
cd scripts && python seed_app_data.py

# ✅ Correct (from project root)
python scripts/seed_app_data.py
```

### Foreign Key Violations

**Problem:** Errors about foreign key constraints

**Solution:** The seeder creates data in the correct order. If you see this error:

1. Ensure your models match the schemas in the seeder
2. Run `reset_db.py` first to clear inconsistent data
3. Check that all model relationships are properly defined

### Duplicate Key Errors

**Problem:** `UniqueViolation` or duplicate key errors

**Solution:** This usually means:

- Data already exists (expected behavior - will be skipped)
- If persistent, run `reset_db.py` to clear all data first

### Performance Issues

**Problem:** Seeding takes too long

**Solution:**

- Reduce the number of attendance records (modify days range in `create_attendance_records`)
- Use `db.bulk_insert_mappings()` for large datasets
- Increase batch sizes

---

## Customization

### Modify Employee Count

In `seed_app_data.py`, edit the `employees_data` list in `create_employees()`:

```python
employees_data = [
    # Add or remove employee dictionaries here
    {
        "name": "New Employee",
        "email": "new@company.com",
        # ... other fields
    }
]
```

### Adjust Attendance Date Range

In `create_attendance_records()`, change the range:

```python
# Current: last 14 days
for days_ago in range(14, 0, -1):

# Change to last 30 days:
for days_ago in range(30, 0, -1):
```

### Modify Payroll Calculations

In `create_payroll_run()`, adjust the simplified calculations for:

- Overtime rates
- Deduction formulas
- Tax bracket logic
- Contribution percentages

---

## Database Schema Requirements

The seeder expects these models to exist:

- `UserDB`, `EmployeeDB`, `AttendanceDB`, `LeaveDB`, `LeaveBalanceDB`
- `CompanyProfileDB`, `HolidayDB`, `BenefitsConfigDB`, `TaxConfigDB`
- `PayrollRunDB`, `PayrollEntryDB`, `PayslipDB`, `MandatoryContributionsDB`

Ensure your SQLAlchemy models match the field names and types used in the seeder.

---

## Next Steps

After seeding:

1. **Verify Data**

   ```bash
   # Check user count
   psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"

   # Check employees
   psql $DATABASE_URL -c "SELECT name, role, department FROM employees;"
   ```

2. **Test Login**

   - Try logging in with seeded credentials
   - Test different user roles (SuperAdmin, Admin)

3. **Run Application**

   ```bash
   uvicorn app.main:app --reload
   ```

4. **Test Features**
   - View attendance records
   - Process payroll
   - Generate payslips
   - Manage leaves

---

## Support

For issues or questions:

1. Check error messages in console output
2. Verify your database connection settings
3. Ensure all dependencies are installed (`pip install -r requirements.txt`)
4. Check model definitions match seeder expectations
