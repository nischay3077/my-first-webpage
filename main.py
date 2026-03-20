import cv2
import os
import time
from database_manager import DatabaseManager

class AttendanceSystem:
    def __init__(self, trainer_path='trainer/trainer.yml'):
        self.db = DatabaseManager()
        self.trainer_path = trainer_path
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.person_details_cache = {} # Cache detailed info by person_id
        
        # UI state for animations/popups
        self.subject = "Unknown"
        self.section = "All"
        self.teacher_name = "Not Logged In"
        self.last_attendance_time = 0
        self.last_attendance_name = ""
        self.last_attendance_details = ""
        self.popup_display_duration = 10 
        self.session_logins = [] # Track everyone logged in this session
        
        self.load_model()

    def set_session_details(self, subject, section, teacher_name):
        self.subject = subject
        self.section = section
        self.teacher_name = teacher_name
        print(f"\n[INFO] Session started for {self.subject} ({self.section}) by {self.teacher_name}")

    def load_model(self):
        if not os.path.exists(self.trainer_path):
            print(f"\n[!] Error: Trainer file not found in 'trainer/'.")
            print("[!] You must register at least one person first using 'add_person.py'.")
            return False
        
        try:
            self.recognizer.read(self.trainer_path)
            print(f"[AI] Model loaded successfully! System ready.")
            return True
        except Exception as e:
            print(f"[!] Error loading model: {e}")
            return False

    def draw_hud_corners(self, frame, x, y, w, h, color, thickness=2, length=20):
        # Top-left
        cv2.line(frame, (x, y), (x + length, y), color, thickness)
        cv2.line(frame, (x, y), (x, y + length), color, thickness)
        # Top-right
        cv2.line(frame, (x + w, y), (x + w - length, y), color, thickness)
        cv2.line(frame, (x + w, y), (x + w, y + length), color, thickness)
        # Bottom-left
        cv2.line(frame, (x, y + h), (x + length, y + h), color, thickness)
        cv2.line(frame, (x, y + h), (x, y + h - length), color, thickness)
        # Bottom-right
        cv2.line(frame, (x + w, y + h), (x + w - length, y + h), color, thickness)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - length), color, thickness)

    def start_recognition(self):
        video_capture = cv2.VideoCapture(0)
        
        if not video_capture.isOpened():
            print("[!] Camera Error: Please check if another app is using the webcam.")
            return

        print(f"\n--- ATTENDANCE SYSTEM RUNNING ({self.subject} - {self.section}) ---")
        print(f"[TEACHER] {self.teacher_name}")
        
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            # --- MODERN OVERLAY ---
            overlay = frame.copy()
            # Top Banner (Modern Glass-like)
            cv2.rectangle(overlay, (20, 20), (frame.shape[1] - 20, 65), (20, 20, 20), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
            
            status_text = f"SESSION ACTIVE | {self.subject} | {self.section}"
            cv2.putText(frame, status_text, (40, 50), cv2.FONT_HERSHEY_DUPLEX, 0.6, (10, 250, 150), 1)
            cv2.putText(frame, f"INSTRUCTOR: {self.teacher_name}", (frame.shape[1] - 250, 50), cv2.FONT_HERSHEY_DUPLEX, 0.5, (200, 200, 200), 1)

            # Process frame
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 8) # Better sensitivity

            # Status Message when NO face is in view
            if len(faces) == 0:
                cv2.putText(frame, "STATUS: SEARCHING FOR SUBJECTS...", (40, 85), cv2.FONT_HERSHEY_DUPLEX, 0.4, (200, 200, 200), 1)
            else:
                cv2.putText(frame, f"STATUS: DETECTED {len(faces)} FACES", (40, 85), cv2.FONT_HERSHEY_DUPLEX, 0.4, (10, 250, 150), 1)

            if not hasattr(self, 'unauthorized_counter'):
                self.unauthorized_counter = 0

            for (x, y, w, h) in faces:
                person_id, confidence = self.recognizer.predict(gray[y:y+h, x:x+w])
                
                # Default status
                color = (255, 255, 255) # White
                label = "SCANNING..."
                sub_label = "Processing..."
                show_details = False

                if confidence < 92: 
                    self.unauthorized_counter = 0 
                    if person_id not in self.person_details_cache:
                        details = self.db.get_person_by_id(person_id)
                        if details:
                            self.person_details_cache[person_id] = details
                    
                    details = self.person_details_cache.get(person_id, {})
                    name = details.get('name', 'Unknown')
                    roll_no = details.get('roll_no', 'N/A')
                    
                    status = self.db.mark_attendance(name, roll_no, self.subject, self.section)
                    
                    show_details = True
                    if status == 1: # NEW SUCCESS
                        color = (10, 255, 10) # Emerald
                        label = f"VERIFIED: {name}"
                        sub_label = f"ID: {roll_no} | LOGGED"
                    elif status == 2: # ALREADY MARKED
                        color = (250, 180, 0) # Gold
                        label = f"MATCH: {name}"
                        sub_label = f"RECORDED PREVIOUSLY"
                    else:
                        color = (100, 100, 100)
                        label = "NOT IN SYSTEM"
                        sub_label = "Access Denied"

                    if self.last_attendance_time == 0 or (name != self.last_attendance_name): 
                        self.last_attendance_time = time.time()
                        self.last_attendance_name = name
                        self.last_attendance_details = label
                    
                    # Update session log
                    log_entry = f"{name} ({roll_no})"
                    if log_entry not in self.session_logins:
                        self.session_logins.append(log_entry)

                else:
                    self.unauthorized_counter += 1
                    color = (0, 100, 255) # Orange
                    label = "IDENTIFYING..."
                    sub_label = "HOLD STILL"

                    if self.unauthorized_counter > 30: 
                        color = (0, 0, 255) # Red
                        label = "UNAUTHORIZED"
                        sub_label = "SECURITY LOGGED"

                        current_time = time.time()
                        if not hasattr(self, 'last_security_log_time'): self.last_security_log_time = 0
                        if current_time - self.last_security_log_time > 15:
                            security_dir = "security_logs"
                            os.makedirs(security_dir, exist_ok=True)
                            img_path = os.path.join(security_dir, f"unauth_{int(current_time)}.jpg")
                            cv2.imwrite(img_path, frame[y:y+h, x:x+w])
                            self.db.log_unauthorized(self.subject, img_path)
                            self.last_security_log_time = current_time

                # Draw Fancy Box
                self.draw_hud_corners(frame, x, y, w, h, color, 3, 25)
                # Semi-transparent label background
                label_box_y = y - 55
                cv2.rectangle(frame, (x, label_box_y), (x + w, y - 5), (30, 30, 30), -1)
                cv2.rectangle(frame, (x, label_box_y), (x + w, y - 5), color, 1)
                
                cv2.putText(frame, label, (x + 8, y - 35), cv2.FONT_HERSHEY_DUPLEX, 0.45, color, 1)
                cv2.putText(frame, sub_label, (x + 8, y - 15), cv2.FONT_HERSHEY_DUPLEX, 0.35, (200, 200, 200), 1)

            # Sidebar with recent activity
            sidebar_x = frame.shape[1] - 220
            cv2.rectangle(frame, (sidebar_x, 80), (frame.shape[1] - 20, frame.shape[0] - 20), (25, 25, 25), -1)
            cv2.rectangle(frame, (sidebar_x, 80), (frame.shape[1] - 20, frame.shape[0] - 20), (60, 60, 60), 1)
            cv2.putText(frame, "RECENT LOGS", (sidebar_x + 15, 110), cv2.FONT_HERSHEY_DUPLEX, 0.5, (10, 250, 150), 1)
            
            for i, log in enumerate(self.session_logins[-12:][::-1]):
                y_pos = 140 + (i * 25)
                cv2.putText(frame, f"> {log[:18]}", (sidebar_x + 15, y_pos), cv2.FONT_HERSHEY_DUPLEX, 0.4, (180, 180, 180), 1)

            window_name = 'Face Recognition Attendance HUD'
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            
            # Check if window was closed via X button
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

        video_capture.release()
        cv2.destroyAllWindows()
        print(f"\n[DONE] System closed.")

if __name__ == "__main__":
    import datetime
    system = AttendanceSystem()
    db = system.db
    
    print("\n" + "*"*40)
    print("      TEACHER LOGIN PORTAL")
    print("*"*40)
    
    t_id = input("Enter Teacher ID: ").strip()
    t_pass = input("Enter Password: ").strip()
    
    teacher_name = db.authenticate_teacher(t_id, t_pass)
    
    if teacher_name:
        print(f"\nWelcome, {teacher_name}!")
        current_day = datetime.datetime.now().strftime("%A")
        print(f"Today is {current_day}.")
        
        timetable = db.get_teacher_timetable(t_id, current_day)
        
        if not timetable:
            print("[!] No classes scheduled for you today.")
        else:
            print("\nYOUR SCHEDULE FOR TODAY:")
            for i, entry in enumerate(timetable):
                print(f" {i+1}. {entry['subject']} ({entry['section']})")
            
            choice = input("\nSelect class number to start (or 'q' to quit): ").strip()
            if choice.lower() != 'q' and choice.isdigit() and 1 <= int(choice) <= len(timetable):
                selected = timetable[int(choice)-1]
                system.set_session_details(selected['subject'], selected['section'], teacher_name)
                system.start_recognition()
            else:
                print("Exiting...")
    else:
        print("\n[!] Invalid Credentials. Access Denied.")
