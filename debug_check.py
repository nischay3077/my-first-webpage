import sqlite3
import os
db_path = os.path.join(os.getcwd(), 'attendance.db')
print(f"Connecting to {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute("SELECT name, roll_no, section FROM persons")
    rows = cursor.fetchall()
    for row in rows:
        print(f"{row[2]} | {row[0]}: {row[1]}")
except Exception as e:
    print(f"Error: {e}")
conn.close()
