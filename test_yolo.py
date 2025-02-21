import cv2
from yolo_detector import YoloFaceDetector

# Khởi tạo model
face_detector = YoloFaceDetector(media_manager=None)

# Load ảnh bằng OpenCV
img1 = cv2.imread("data_test/thiennhien.jpg")
img2 = cv2.imread("data_test/2person.jpg")

# Tạo list ảnh
imgs = [img1, img2]

# Chạy face detection
results = face_detector.get_face_detects(imgs, verbose=True)



all_cropped_faces = []
metadata = []
face_counts = []

# # In kết quả
# for i, faces in enumerate(results):
#     print(f"Ảnh {i+1}: {len(faces)} khuôn mặt")
#     for face in faces:
#         print(face)  # Mỗi face là numpy array [x1, y1, x2, y2, conf]

for i, faces in enumerate(results):
    if not faces:  # Nếu danh sách rỗng (không có khuôn mặt)
        face_counts.append(0)
        continue

    for bbox in faces:
        metadata.append({
            "image_index": i,
            "bbox": bbox
        })
        cropped_faces = face_detector.crop_faces(imgs[i], faces=faces, margin=10)


for i, face in enumerate(cropped_faces):
    cv2.imshow(f"Face {i+1}", face)

cv2.waitKey(0)
cv2.destroyAllWindows()