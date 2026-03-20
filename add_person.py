import cv2
import os
import time
from database_manager import DatabaseManager
from trainer import train_faces

def capture_person():
    db = DatabaseManager()
    images_dir = 'dataset/'
    os.makedirs(images_dir, exist_ok=True)
    
    # 📋 Step 1: Get Details
    print("\n--- NEW STUDENT REGISTRATION ---")
    name = input("Enter Full Name: ").strip()
    roll_no = input("Enter Roll No (e.g., 36): ").strip()
    section = input("Enter Section (e.g., BCA AIDS B1): ").strip()
    role = input("Enter Role (default: Student): ").strip() or 'Student'
    
    # 💾 Step 2: Save to DB & Get ID
    person_id = db.add_person(name, roll_no, section, role)
    if person_id is None:
        print("[!] FATAL ERROR: Could move database record.")
        return
    
    # 📸 Step 3: Face Capture
    video_capture = cv2.VideoCapture(0)
    face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    if not video_capture.isOpened():
        print("[!] CAMERA ERROR: Please check if another app is using the webcam.")
        return

    # 🖼️ Bring camera window to front
    window_name = 'REGISTRATION: PLEASE LOOK AT CAMERA'
    cv2.namedWindow(window_name)
    cv2.moveWindow(window_name, 400, 200)

    print(f"\n[INFO] Starting capture for {name} (ID: {person_id})")
    print("[INFO] IMPORTANT: Make sure your face is visible and stable.")
    print("[INFO] Press 'q' to cancel if needed.")
    
    count = 0
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(gray, 1.2, 5) # Better detection
        
        # UI Overlay
        cv2.putText(frame, f"Registering: {name}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
        cv2.putText(frame, f"Samples: {count}/30", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)

        for (x, y, w, h) in faces:
            count += 1
            # 📁 Format: User.{id}.{sample_no}.jpg
            sample_path = f"dataset/User.{person_id}.{count}.jpg"
            cv2.imwrite(sample_path, gray[y:y+h, x:x+w])
            
            # Visualization
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.waitKey(250) # Increased delay (0.25s) for better quality samples
            
        cv2.imshow(window_name, frame)
        
        if (cv2.waitKey(1) & 0xFF == ord('q')) or count >= 30:
            break
            
    video_capture.release()
    cv2.destroyAllWindows()
    
    # 🤖 Step 4: AI Training
    if count >= 30:
        print("\n[AI] Processing images... Please wait.")
        train_faces()
        print(f"\n[SUCCESS] Registration Complete for {name}!")
        print("[!] You can now start the attendance system using 'main.py'")
    else:
        print("\n[CANCELLED] Registration data was not fully captured.")

if __name__ == "__main__":
    capture_person()
