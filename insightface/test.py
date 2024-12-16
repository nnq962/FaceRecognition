from deepface import DeepFace
import time

start = time.time()
# anti spoofing test in face detection
face_objs = DeepFace.extract_faces(
  img_path="datatest/nnq1.jpg",
  anti_spoofing = True
)

print("Time process:", time.time() - start)
print(face_objs)