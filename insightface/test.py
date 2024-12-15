import faiss
import numpy as np
import cv2
import pickle
from insightface_detector import InsightFaceDetector

detector = InsightFaceDetector()

# Load FAISS index
index = faiss.read_index("face_index.faiss")

# Load ánh xạ
with open("index_to_id.pkl", "rb") as f:
    index_to_id = pickle.load(f)

# Tìm kiếm khuôn mặt
query_img = cv2.imread("photo_test/suprise.png")  # Đọc ảnh query
result = detector.get_face_detect(query_img)[0][0]  # Phát hiện khuôn mặt
query_embedding = detector.get_face_embedding(query_img, result[0], result[1], result[2])

# Thực hiện tìm kiếm
D, I = index.search(np.array([query_embedding]).astype('float32'), k=5)  # Tìm 5 kết quả gần nhất

threshold = 0.5  # Đặt ngưỡng độ tương đồng
found_match = False  # Biến theo dõi xem có kết quả khớp hay không

for i, idx in enumerate(I[0]):
    similarity = D[0][i]
    if similarity >= threshold:
        person_id, image_name = index_to_id[idx]
        print(f"Match {i+1}: ID={person_id}, Image={image_name}, Similarity={similarity:.4f}")
        found_match = True

if not found_match:
    print("No confident match found. Query does not belong to the database.")