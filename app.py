import os
import cv2
import numpy as np
import base64
import datetime
import sqlite3
import socket
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from database_manager import DatabaseManager

def get_local_ip():
    """Get the local network IP address of the machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

app = Flask(__name__)
app.secret_key = "attendance_secret_key"
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=2)

db = DatabaseManager()

# Load the recognition model at startup
recognizer = cv2.face.LBPHFaceRecognizer_create()
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

TRAINER_PATH = 'trainer/trainer.yml'

def load_recognition_model():
    """Helper to load/reload the latest trainer file."""
    if os.path.exists(TRAINER_PATH):
        try:
            recognizer.read(TRAINER_PATH)
            print(f"[AI] Model (re)loaded from {TRAINER_PATH}")
            return True
        except Exception as e:
            print(f"[!] Error loading trainer: {e}")
    else:
        print("[!] Warning: Trainer not found.")
    return False

load_recognition_model()

@app.route('/')
def index():
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    # Support both JSON and Form Data
    if request.is_json:
        data = request.get_json()
        teacher_id = data.get('username') or data.get('teacher_id')
        password = data.get('password')
    else:
        teacher_id = request.form.get('username')
        password = request.form.get('password')
        
    teacher_name = db.authenticate_teacher(teacher_id, password)
    
    if teacher_name:
        session['teacher_id'] = teacher_id
        session['teacher_name'] = teacher_name
        if request.is_json:
            return jsonify({"success": True})
        return redirect(url_for('dashboard'))
        
    if request.is_json:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    return render_template('index.html', error="Invalid Faculty ID or Password")

@app.route('/dashboard')
def dashboard():
    if 'teacher_id' not in session: return redirect(url_for('index'))
    current_day = datetime.datetime.now().strftime("%A")
    current_month = datetime.datetime.now().strftime("%B").upper() # "MARCH"
    
    timetable = db.get_teacher_timetable(session['teacher_id'], current_day)
    
    # Get and sort students by roll number numerically for 'series' consistency
    students = db.get_all_students_for_teacher(session['teacher_id'])
    
    # Check enrollment status for each student
    dataset_dir = 'dataset/'
    for s in students:
        s['is_enrolled'] = os.path.exists(os.path.join(dataset_dir, f"User.{s['id']}.1.jpg"))
    
    students.sort(key=lambda x: (x['section'], int(x['roll_no']) if x['roll_no'].isdigit() else 999))

    # Calculate dynamic Average Attendance for the teacher
    total_batch_size = len(students)
    unique_attendees_today = 0
    if total_batch_size > 0:
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT person_id) FROM attendance WHERE date = ?", (today_str,))
        unique_attendees_today = cursor.fetchone()[0]
        conn.close()
        avg_attendance = round((unique_attendees_today / (total_batch_size if total_batch_size > 0 else 1)) * 100)
    else:
        avg_attendance = 0

    return render_template('dashboard.html', 
                         teacher_name=session['teacher_name'], 
                         current_day=current_day, 
                         current_month=current_month,
                         timetable=timetable,
                         students=students,
                         avg_attendance=avg_attendance,
                         datetime=datetime)


@app.route('/mark-attendance/<subject>/<section>')
def mark_attendance_page(subject, section):
    if 'teacher_id' not in session: return redirect(url_for('index'))
    server_ip = get_local_ip()
    return render_template('mark_attendance.html', subject=subject, section=section, server_ip=server_ip)

@app.route('/attendance')
def attendance():
    if 'teacher_id' not in session: return redirect(url_for('index'))
    
    subject = request.args.get('subject')
    date = request.args.get('date')
    
    df = db.get_attendance_filtered(subject, date)
    records = df.to_dict('records')
    
    # Simple chart data: Count per subject
    subject_counts = df['subject'].value_counts().to_dict() if not df.empty else {}
    
    # Get distinct subjects for the filter dropdown
    teacher_subjects = db.get_distinct_subjects(session['teacher_id'])
    
    # NEW: Get total students in the section for the selected subject (to show Nischay + 19 others)
    section_students = []
    attendance_rate = 0
    if subject:
        # We assume teachers teach specific sections. Let's find the section for this subject.
        timetable = db.get_teacher_timetable(session['teacher_id'], datetime.datetime.now().strftime("%A"))
        matched_section = next((item['section'] for item in timetable if item['subject'] == subject), None)
        
        if matched_section:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM persons WHERE section = ?', (matched_section,))
            section_students = [r[0] for r in cursor.fetchall()]
            conn.close()
            
            if len(section_students) > 0:
                unique_attendees = df['name'].nunique() if not df.empty else 0
                attendance_rate = round((unique_attendees / len(section_students)) * 100, 1)

    # DEFAULT: If no subject, show total students in all sections taught by teacher
    if not subject:
        total_enrollment = db.get_all_students_for_teacher(session['teacher_id'])
        section_students = [s['name'] for s in total_enrollment]
        if len(section_students) > 0:
            unique_attendees = df['name'].nunique() if not df.empty else 0
            attendance_rate = round((unique_attendees / len(section_students)) * 100, 1)

    return render_template('attendance.html', 
                         records=records, 
                         subject_counts=subject_counts,
                         teacher_subjects=teacher_subjects,
                         selected_subject=subject,
                         selected_date=date,
                         total_students=len(section_students),
                         attendance_rate=attendance_rate)

@app.route('/weekly-report/<subject>/<section>')
def weekly_report(subject, section):
    if 'teacher_id' not in session: return redirect(url_for('index'))
    
    current_month = datetime.datetime.now().strftime("%B").upper() # "MARCH"
    offset = int(request.args.get('week', 0)) # 0 current, -1 last week
    df, start_date, end_date = db.get_weekly_attendance(subject, section, offset)
    
    # Process into a student list to maintain sorting
    days_list = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    days_map = {'1': 'Mon', '2': 'Tue', '3': 'Wed', '4': 'Thu', '5': 'Fri', '6': 'Sat', '0': 'Sun'}
    
    # Ensure dataframe is sorted by name
    df = df.sort_values(by=['name'])
    
    # Use an OrderredDict or a list of dicts to preserve alphabetical order
    enrollment = db.get_all_students_for_teacher(session['teacher_id'])
    # Filter for this section and sort by numeric roll number
    section_students = sorted([s for s in enrollment if s['section'] == section], 
                             key=lambda x: int(x['roll_no']) if x['roll_no'].isdigit() else 999)
    
    processed_list = []
    for s in section_students:
        student_attendance = {d: False for d in days_list}
        # Filter attendance for this specific student
        student_df = df[df['name'] == s['name']]
        for _, row in student_df.iterrows():
            if row['day_num'] is not None:
                day_name = days_map.get(str(row['day_num']))
                if day_name:
                    student_attendance[day_name] = True
        
        processed_list.append({
            "name": s['name'],
            "roll_no": s['roll_no'],
            "attendance": student_attendance
        })

    return render_template('weekly_report.html', 
                         subject=subject, 
                         section=section, 
                         current_month=current_month,
                         report_data=processed_list,
                         days=days_list,
                         start_date=start_date,
                         end_date=end_date,
                         offset=offset)

@app.route('/register/<int:person_id>')
def register_face(person_id):
    if 'teacher_id' not in session: return redirect(url_for('index'))
    person = db.get_person_by_id(person_id)
    if not person: return "Student not found", 404
    return render_template('register.html', person=person, person_id=person_id)

@app.route('/student-checkin/<subject>/<section>')
def student_checkin_page(subject, section):
    """Mobile-friendly check-in page for students."""
    return render_template('student_checkin.html', subject=subject, section=section)

@app.route('/verify-checkin', methods=['POST'])
def verify_checkin():
    """Verify student identity via face and mark attendance."""
    try:
        load_recognition_model()
        data = request.json
        img_data = data['image'].split(",")[1]
        subject = data.get('subject')
        section = data.get('section')
        
        img_bytes = base64.b64decode(img_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
        
        faces = face_cascade.detectMultiScale(img, 1.2, 5)
        if len(faces) == 0:
            return jsonify({"status": "no_face", "msg": "No face detected"})
            
        for (x, y, w, h) in faces:
            id, confidence = recognizer.predict(img[y:y+h, x:x+w])
            
            # Use strict threshold for check-in
            if confidence < 75:
                person = db.get_person_by_id(id)
                if person:
                    # ENSURE STUDENT IS IN THE RIGHT SECTION
                    # (Allowing cross-section recognition but logging actual section)
                    db.mark_attendance(person['name'], person['roll_no'], subject, section)
                    return jsonify({
                        "status": "success", 
                        "name": person['name'],
                        "msg": f"Check-in successful! Welcome, {person['name']}."
                    })
            
        return jsonify({"status": "error", "msg": "Identity not recognized. Please scan correctly."})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/save-sample', methods=['POST'])
def save_sample():
    data = request.json
    person_id = data['person_id']
    img_data = data['image'].split(",")[1]
    count = data['count']
    
    img_bytes = base64.b64decode(img_data)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
    
    # Save face sample
    os.makedirs('dataset', exist_ok=True)
    cv2.imwrite(f"dataset/User.{person_id}.{count}.jpg", img)
    
    if count >= 30:
        # Re-train model
        from trainer import train_faces
        train_faces()
        
    return jsonify({"status": "success"})

@app.route('/check-duplicate-face', methods=['POST'])
def check_duplicate_face():
    try:
        # ALWAYS reload to catch newly registered students
        load_recognition_model()
        
        data = request.json
        img_data = data['image'].split(",")[1]
        current_person_id = int(data.get('person_id', -1))
        
        img_bytes = base64.b64decode(img_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
        
        faces = face_cascade.detectMultiScale(img, 1.2, 5)
        
        if len(faces) == 0:
            return jsonify({"status": "no_face"})
            
        for (x, y, w, h) in faces:
            id, confidence = recognizer.predict(img[y:y+h, x:x+w])
            
            # Use a slightly more inclusive threshold for duplicate detection (e.g., < 95)
            # Since we want to prevent ANY similarity that might be a proxy.
            if confidence < 95:
                # If it matches SOMEONE ELSE
                if id != current_person_id:
                    person = db.get_person_by_id(id)
                    if person:
                        return jsonify({
                            "status": "duplicate", 
                            "name": person['name'], 
                            "roll_no": person['roll_no'],
                            "section": person['section'],
                            "id": id,
                            "confidence": round(100 - confidence, 2)
                        })
        
        return jsonify({"status": "unique"})
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/recognize', methods=['POST'])
def recognize():
    global unknown_counter
    try:
        # Reload model to ensure latest session captures are recognized
        load_recognition_model()
        
        data = request.json
        img_data = data['image'].split(",")[1]
        subject = data.get('subject', 'General')
        
        img_bytes = base64.b64decode(img_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return jsonify({"status": "no_face"})
            
        for (x, y, w, h) in faces:
            id, confidence = recognizer.predict(gray[y:y+h, x:x+w])
            
            # Confidence < 100 means good match for LBPH
            if confidence < 70:
                person = db.get_person_by_id(id)
                if person:
                    # IMPORTANT: Use the session's current section to mark attendance, 
                    # not the student's native section, to allow cross-section recognition.
                    db.mark_attendance(person['name'], person['roll_no'], subject, data.get('section', person['section']))
                    unknown_counter = 0 # Reset on match
                    return jsonify({"status": "match", "name": person['name'], "confidence": round(100 - confidence, 2)})
            else:
                unknown_counter += 1
                if unknown_counter >= 5:
                    # Save intruder snapshot in the designated folder
                    os.makedirs('security_logs', exist_ok=True)
                    img_name = f"intruder_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    img_path = os.path.join('security_logs', img_name)
                    cv2.imwrite(img_path, img)
                    
                    # Log to DB using the same path format used by the route
                    db.log_unauthorized(subject, img_path)
                    unknown_counter = 0 # Reset after logging incident
                    return jsonify({"status": "security_alert", "msg": "Repeated unauthorized access! Snapshot recorded."})
                    
        return jsonify({"status": "unknown"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/security-logs')
def security_logs():
    if 'teacher_id' not in session: return redirect(url_for('index'))
    logs = db.get_security_logs()
    return render_template('security_logs.html', logs=logs)

# Global counter for security tracking
unknown_counter = 0

from flask import send_from_directory
@app.route('/security_logs/<path:filename>')
def serve_security_logs(filename):
    return send_from_directory('security_logs', filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
