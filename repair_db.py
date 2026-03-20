"""
DB Repair Script
================
Run this if your DB was reset but your face dataset and trainer.yml still exist.
It will re-add your person record to the DB with the correct ID, and optionally retrain.
"""
import sqlite3
import os
from database_manager import DatabaseManager
from trainer import train_faces

def repair():
    db = DatabaseManager()
    conn = sqlite3.connect('db/attendance.db')
    cursor = conn.cursor()

    print("\n" + "="*50)
    print("   🔧 ATTENDANCE SYSTEM - REPAIR TOOL")
    print("="*50)
    print("[INFO] Your dataset has these User IDs:")
    
    # Find all user IDs from dataset folder
    user_ids = set()
    for f in os.listdir('dataset'):
        parts = f.replace('.jpg', '').split('.')
        if len(parts) >= 2 and parts[0] == 'User':
            user_ids.add(int(parts[1]))
    
    for uid in sorted(user_ids):
        print(f"  - User ID: {uid}")

    print("\n[INPUT] Enter details for each User ID:")
    
    for uid in sorted(user_ids):
        # Check if already exists
        cursor.execute('SELECT name FROM persons WHERE id = ?', (uid,))
        existing = cursor.fetchone()
        if existing:
            print(f"  [SKIP] User ID {uid} already in DB as '{existing[0]}'")
            continue
        
        print(f"\n--- User ID {uid} ---")
        name     = input("  Enter Full Name    : ").strip()
        roll_no  = input("  Enter Roll No      : ").strip()
        section  = input("  Enter Section      : ").strip()
        
        # Insert with explicit ID so it matches the trainer model
        cursor.execute(
            'INSERT OR IGNORE INTO persons (id, name, roll_no, section, role) VALUES (?, ?, ?, ?, ?)',
            (uid, name, roll_no, section, 'Student')
        )
        conn.commit()
        print(f"  [OK] Registered '{name}' with ID {uid}")

    conn.close()

    retrain = input("\nDo you want to retrain the AI model now? (y/n): ").strip().lower()
    if retrain == 'y':
        print("\n[AI] Retraining model...")
        train_faces()
        print("[SUCCESS] Model retrained. System is now ready!")
    else:
        print("[INFO] Skipped retraining. Using existing trainer.yml")

    print("\n[DONE] Repair complete. Run main.py or app.py to start attendance.")

if __name__ == "__main__":
    repair()
