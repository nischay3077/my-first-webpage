import sqlite3
import os
import shutil

# 1. Clear Dataset
dataset_dir = 'dataset'
if os.path.exists(dataset_dir):
    shutil.rmtree(dataset_dir)
os.makedirs(dataset_dir)
print(f"Cleared dataset folder.")

# 2. Clear Trainer
trainer_path = 'trainer/trainer.yml'
if os.path.exists(trainer_path):
    os.remove(trainer_path)
print(f"Removed trainer file.")

# 3. Clear Database Records
from database_manager import DatabaseManager
db = DatabaseManager()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()
cursor.execute("DELETE FROM attendance")
cursor.execute("DELETE FROM security_logs")
cursor.execute("DELETE FROM persons")
cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('attendance', 'security_logs', 'persons')")
conn.commit()
conn.close()

# Re-seed the students
db.seed_sample_data()
print("Database tables cleared and re-seeded.")

# 4. Clear Security Logs
sec_dir = 'security_logs'
if os.path.exists(sec_dir):
    shutil.rmtree(sec_dir)
os.makedirs(sec_dir)
print("Cleared security logs.")
