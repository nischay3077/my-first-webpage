import sqlite3
import os

db_path = 'db/attendance.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted existing database: {db_path}")

# Import the DatabaseManager to re-create and re-seed
from database_manager import DatabaseManager
db = DatabaseManager()
print("Database re-initialized and re-seeded successfully.")
