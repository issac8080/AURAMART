"""
Initialize the returns database with tables.
Run this once to create the database schema.
"""
from app.returns.db import engine, init_db
from app.returns.db_models import Base

print("Creating returns database tables...")
Base.metadata.create_all(bind=engine)
print("[OK] Returns database initialized successfully!")
print("  - returns table created")
print("  - orders table created")
print("  - policies table created")
print("\nYou can now use the return & exchange module!")
