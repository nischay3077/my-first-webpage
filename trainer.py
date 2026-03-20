import cv2
import os
import numpy as np
import pickle

# Function to extract ID from image filenames
def get_images_and_labels(images_dir, detector):
    image_paths = [os.path.join(images_dir, f) for f in os.listdir(images_dir)]
    face_samples = []
    ids = []
    
    for image_path in image_paths:
        if not image_path.endswith('.jpg'):
            continue
            
        # Filename format: User.{id}.{sample_no}.jpg
        try:
            filename = os.path.split(image_path)[-1]
            person_id = int(filename.split('.')[1])
            
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Detect faces again to ensure we have clear samples
            faces = detector.detectMultiScale(gray)
            for (x, y, w, h) in faces:
                face_samples.append(gray[y:y+h, x:x+w])
                ids.append(person_id)
        except Exception as e:
            print(f"Skipping {image_path}: {e}")
            
    return face_samples, ids

def train_faces(images_dir='dataset/', trainer_path='trainer/trainer.yml'):
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    print(f"\n[AI] Training model using images in {images_dir}...")
    faces, ids = get_images_and_labels(images_dir, detector)
    
    if len(faces) > 0:
        recognizer.train(faces, np.array(ids))
        os.makedirs(os.path.dirname(trainer_path), exist_ok=True)
        recognizer.save(trainer_path)
        print(f"[AI] Model trained successfully! {len(set(ids))} persons learned.")
    else:
        print("[AI] Error: No face data found for training.")

if __name__ == "__main__":
    train_faces()
