from yolo_detector import YoloDetector
import cv2

img1 = cv2.imread("data_test/nnq1.jpg")
img2 = cv2.imread("data_test/thiennhien.jpg")
imgs = [img1, img2]
detector = YoloDetector()

result = detector.get_face_detects(imgs, verbose=False)
# Kiểm tra từng ảnh xem có khuôn mặt hay không
for idx, faces in enumerate(result):
    print(faces.type())
    if not faces:
        print(f"Ảnh {idx} không có khuôn mặt")
    else:
        print(f"Ảnh {idx} có {len(faces)} khuôn mặt")


print(result)