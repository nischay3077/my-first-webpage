import sqlite3
import datetime
import os
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path='db/attendance.db'):
        self.db_path = db_path
        self.ensure_db_exists()

    def ensure_db_exists(self):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for storing person data (Students)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS persons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_no TEXT,
                section TEXT,
                role TEXT DEFAULT 'Student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, roll_no, section)
            )
        ''')

        # Table for Teachers (App Users)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # Table for Timetables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timetables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT,
                day_of_week TEXT, -- Monday, Tuesday, etc.
                subject TEXT,
                section TEXT,
                FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id)
            )
        ''')
        
        # Table for storing attendance logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                subject TEXT,
                section TEXT,
                date DATE,
                time TIME,
                FOREIGN KEY(person_id) REFERENCES persons(id)
            )
        ''')
        
        # Table for security logs (Unauthorized access)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                image_path TEXT,
                date DATE,
                time TIME
            )
        ''')
            
        conn.commit()
        conn.close()
        self.seed_sample_data()

    def seed_sample_data(self):
        """Add sample teachers and timetables for testing if tables are empty."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if teachers empty
        cursor.execute('SELECT COUNT(*) FROM teachers')
        if cursor.fetchone()[0] == 0:
            # Add sample teacher: ID=prof_sharma, Pass=1234
            cursor.execute('INSERT INTO teachers (teacher_id, name, password) VALUES (?, ?, ?)', 
                           ('prof_sharma', 'Prof. Sharma', '1234'))
            cursor.execute('INSERT INTO teachers (teacher_id, name, password) VALUES (?, ?, ?)', 
                           ('prof_verma', 'Prof. Verma', '4321'))
            
            # Add sample timetables - 4 subjects per day
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            for day in days:
                # Prof Sharma
                cursor.execute('INSERT INTO timetables (teacher_id, day_of_week, subject, section) VALUES (?, ?, ?, ?)',
                               ('prof_sharma', day, 'Java Programming', 'BCA Sec A'))
                cursor.execute('INSERT INTO timetables (teacher_id, day_of_week, subject, section) VALUES (?, ?, ?, ?)',
                               ('prof_sharma', day, 'Python AI', 'MCA Sec B'))
                cursor.execute('INSERT INTO timetables (teacher_id, day_of_week, subject, section) VALUES (?, ?, ?, ?)',
                               ('prof_sharma', day, 'Data Structures', 'BCA Sec C'))
                cursor.execute('INSERT INTO timetables (teacher_id, day_of_week, subject, section) VALUES (?, ?, ?, ?)',
                               ('prof_sharma', day, 'Machine Learning', 'MCA Sec A'))
                
                # Prof Verma
                cursor.execute('INSERT INTO timetables (teacher_id, day_of_week, subject, section) VALUES (?, ?, ?, ?)',
                               ('prof_verma', day, 'Digital Marketing', 'MCA Sec B'))

        # Seed students if table is empty
        cursor.execute('SELECT COUNT(*) FROM persons')
        if cursor.fetchone()[0] == 0:
            # Categorized pools to ensure every batch is distinct and professional
            section_data = {
                "BCA Sec A": ["Nischay", "Araf", "Aditya", "Ananya", "Diya", "Aman", "Amrita", "Anika", "Arjun", "Aryan", "Avni", "Bhavya", "Darshana", 
                             "Esha", "Gaurav", "Harsh", "Isha", "Jatin", "Komal", "Lakshay"],
                "MCA Sec B": ["Nischay", "Diya", "Abhay", "Binny", "Chanda", "Deepak", "Devi", "Divya", "Fateh", "Gopal", "Hridyanshu", "Indu",
                             "Jaya", "Jyoti", "Karan", "Kavya", "Madhav", "Mamta", "Mithun", "Nikita"],
                "BCA Sec C": ["Nischay", "Chetan", "Ciya", "Dhruv", "Disha", "Ekta", "Gauri", "Hina", "Indra", "Jeevan", "Kiran",
                             "Lata", "Mehak", "Naveen", "Nisha", "Ojas", "Pankaj", "Praniti", "Rahul", "Riya", "Sahil"],
                "MCA Sec A": ["Nischay", "Neer", "Oshina", "Pari", "Prathmesh", "Pranav", "Rashi", "Rohan", "Siddharth", "Sumit",
                             "Tanya", "Tanvi", "Udit", "Ujjwal", "Vansh", "Vihaan", "Vidita", "Yash", "Zoya", "Zeeshan"]
            }
            
            all_students = []
            for section, names in section_data.items():
                # Sort alphabetically to ensure both names and roll numbers are in 'series'
                sorted_names = sorted(list(set(names))) # Use set to avoid any duplicates
                
                for index, name in enumerate(sorted_names):
                    roll_no = index + 1
                    all_students.append((name, str(roll_no), section))
            
            # Since Nischay and Diya might exist with different roll numbers in different sections,
            # we should handle the UNIQUE constraint if we were to re-run.
            # For seeding, we'll just insert if they don't exist.
            cursor.executemany('INSERT OR IGNORE INTO persons (name, roll_no, section) VALUES (?, ?, ?)', all_students)
        
        conn.commit()
        conn.close()

    def get_weekly_attendance(self, subject, section, week_offset=0):
        """Get attendance for a specific subject and section for a chosen week."""
        conn = sqlite3.connect(self.db_path)
        
        # Calculate date range for the requested week
        # week_offset=0 is current week, -1 is previous week, etc.
        today = datetime.datetime.now()
        start_of_week = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(weeks=week_offset)
        end_of_week = start_of_week + datetime.timedelta(days=6)
        
        start_str = start_of_week.strftime("%Y-%m-%d")
        end_str = end_of_week.strftime("%Y-%m-%d")
        
        query = f'''
            SELECT 
                p.name, 
                p.roll_no,
                strftime('%w', a.date) as day_num,
                a.date
            FROM persons p
            LEFT JOIN attendance a ON p.id = a.person_id 
                AND a.subject = ? 
                AND a.section = ?
                AND a.date BETWEEN '{start_str}' AND '{end_str}'
            WHERE p.section = ?
            ORDER BY p.name, a.date
        '''
        df = pd.read_sql_query(query, conn, params=(subject, section, section))
        conn.close()
        return df, start_str, end_str

    def log_unauthorized(self, subject, image_path):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        
        cursor.execute('INSERT INTO security_logs (subject, image_path, date, time) VALUES (?, ?, ?, ?)', 
                      (subject, image_path, date_str, time_str))
        conn.commit()
        conn.close()
        print(f"[SECURITY] Unauthorized access logged for {subject}")


    def add_person(self, name, roll_no, section, role='Student'):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO persons (name, roll_no, section, role) VALUES (?, ?, ?, ?)', 
                           (name, roll_no, section, role))
            conn.commit()
            person_id = cursor.lastrowid
            print(f"[DB] Registered: {name} (ID: {person_id})")
            return person_id
        except sqlite3.IntegrityError:
            # If exists, return the existing ID
            cursor.execute('SELECT id FROM persons WHERE name = ? AND roll_no = ?', (name, roll_no))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def get_person_by_id(self, person_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name, roll_no, section, role FROM persons WHERE id = ?', (person_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"name": result[0], "roll_no": result[1], "section": result[2], "role": result[3]}
        return None

    def get_all_students_for_teacher(self, teacher_id):
        """Get all students in sections taught by this teacher."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Find sections taught by teacher
        cursor.execute('SELECT DISTINCT section FROM timetables WHERE teacher_id = ?', (teacher_id,))
        sections = [r[0] for r in cursor.fetchall()]
        
        if not sections: return []
        
        # Get students in those sections
        placeholders = ', '.join(['?'] * len(sections))
        query = f'SELECT id, name, roll_no, section FROM persons WHERE section IN ({placeholders}) ORDER BY section, name'
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, sections)
        results = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "roll_no": r[2], "section": r[3]} for r in results]

    def authenticate_teacher(self, teacher_id, password):
        """Verify teacher login credentials."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM teachers WHERE teacher_id = ? AND password = ?', (teacher_id, password))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_teacher_timetable(self, teacher_id, day_of_week):
        """Fetch subjects and sections for a teacher on a specific day."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT subject, section FROM timetables WHERE teacher_id = ? AND day_of_week = ?', (teacher_id, day_of_week))
        results = cursor.fetchall()
        conn.close()
        return [{"subject": r[0], "section": r[1]} for r in results]

    def mark_attendance(self, name, roll_no, subject, section="All"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Look for person by name and roll_no
        cursor.execute('SELECT id, section FROM persons WHERE name = ?', (name,))
        results = cursor.fetchall()
        
        person_id = None
        if results:
            # 1. Look for a record that matches THIS specific section
            for r_id, r_section in results:
                if r_section == section:
                    person_id = r_id
                    break
            
            # 2. If no match in this section, just use the first one found (legacy behavior)
            if not person_id:
                person_id = results[0][0]
        
        if person_id:
            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            
            # Check if already marked for THIS SPECIFIC subject and section today
            cursor.execute('''
                SELECT * FROM attendance 
                WHERE person_id = ? AND date = ? AND subject = ? AND section = ?
            ''', (person_id, date_str, subject, section))
            
            if not cursor.fetchone():
                cursor.execute('INSERT INTO attendance (person_id, subject, section, date, time) VALUES (?, ?, ?, ?, ?)', 
                             (person_id, subject, section, date_str, time_str))
                conn.commit()
                print(f"[SUCCESS] {name} logged in for {subject} ({section})")
                conn.close()
                return 1 # New Success
            else:
                conn.close()
                return 2 # Already Marked
        
        conn.close()
        return 0 # Fail to find

    def get_attendance_report(self):
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT 
                p.name, 
                p.roll_no, 
                p.section, 
                CASE 
                    WHEN a.subject IS NULL OR a.subject = '' THEN 'Not Recorded'
                    ELSE a.subject 
                END as subject,
                a.date, 
                a.time 
            FROM attendance a
            JOIN persons p ON a.person_id = p.id
            ORDER BY a.date DESC, a.time DESC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    def get_security_logs(self):
        conn = sqlite3.connect(self.db_path)
        query = "SELECT subject, image_path, date, time FROM security_logs ORDER BY date DESC, time DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_dict('records')

    def get_distinct_subjects(self, teacher_id):
        """Get list of unique subjects taught by this teacher."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT subject FROM timetables WHERE teacher_id = ?', (teacher_id,))
        subjects = [r[0] for r in cursor.fetchall()]
        conn.close()
        return subjects

    def get_attendance_filtered(self, subject=None, date=None):
        """Get attendance report with optional filtering."""
        conn = sqlite3.connect(self.db_path)
        query = '''
            SELECT 
                p.name, 
                p.roll_no, 
                p.section, 
                a.subject,
                a.date, 
                a.time 
            FROM attendance a
            JOIN persons p ON a.person_id = p.id
            WHERE 1=1
        '''
        params = []
        if subject:
            query += " AND a.subject = ?"
            params.append(subject)
        if date:
            query += " AND a.date = ?"
            params.append(date)
            
        query += " ORDER BY a.date DESC, a.time DESC"
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df

if __name__ == "__main__":
    db = DatabaseManager()
    print("Database synced successfully!")
