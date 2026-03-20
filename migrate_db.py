import sqlite3

conn = sqlite3.connect('db/attendance.db')
cursor = conn.cursor()

# Try to add 'section' column to attendance table if it doesn't exist
try:
    cursor.execute("ALTER TABLE attendance ADD COLUMN section TEXT DEFAULT 'All'")
    conn.commit()
    print("[OK] 'section' column added to attendance table.")
except sqlite3.OperationalError as e:
    print(f"[INFO] {e} (column may already exist)")

# Print current table state
print("\n--- Tables ---")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f"  {t[0]}")

print("\n--- Teachers ---")
teachers = cursor.execute("SELECT * FROM teachers").fetchall()
for t in teachers:
    print(f"  {t}")

print(f"\n--- Timetable count ---")
count = cursor.execute("SELECT COUNT(*) FROM timetables").fetchone()[0]
print(f"  {count} entries")

conn.close()
print("\n[DONE] Database ready.")
