import cv2
from insightface_detector import InsightFaceDetector
from fer import FER
import numpy as np
import time
from face_emotion import FERUtils

fer_class = FERUtils()

# Khởi tạo các đối tượng cần thiết
fer_model = FER()
detector = InsightFaceDetector(media_manager=None)

# Đọc ảnh
img = cv2.imread("data_test/2person.jpg")
pred = detector.get_face_detects(img)

# Kiểm tra nếu có khuôn mặt được phát hiện
emotion_count = 0
batch_bbox = []
if pred and pred[0]:
    bboxes, keypoints = pred[0]  # Lấy bounding boxes và keypoints từ kết quả

    # Tính thời gian xử lý từng khuôn mặt
    start_time = time.perf_counter()
    for bbox, kps in zip(bboxes, keypoints):
        x1, y1, x2, y2, conf = bbox.astype(int)  # Chuyển bounding box về kiểu int
        bbox_test = [x1, y1, x2, y2]
        batch_bbox.append(np.array(bbox_test))

        # Phát hiện cảm xúc từng khuôn mặt
        emotion = fer_model.detect_emotions(img, [bbox_test])
        print(f"Emotion for bbox {bbox_test}: {emotion}")
        emotion_count += 1

    end_time = time.perf_counter()
    print("Time process (per face):", end_time - start_time)
    print("Emotion count:", emotion_count)

    # Vẽ bounding boxes và keypoints lên ảnh
    for bbox, kps in zip(bboxes, keypoints):
        x1, y1, x2, y2, conf = bbox.astype(int)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        for kp in kps:
            kp_x, kp_y = kp.astype(int)
            cv2.circle(img, (kp_x, kp_y), 3, (0, 0, 255), -1)

    cv2.imshow("Detected Faces", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Tính thời gian xử lý cả batch
    start_time_batch = time.perf_counter()
    emotions = fer_class.analyze_face(img, batch_bbox)
    dominant_emotions = fer_class.get_dominant_emotions(emotions)
    end_time_batch = time.perf_counter()
    print(f"Batch emotions: {dominant_emotions}")
    print("Time process (batch):", end_time_batch - start_time_batch)
else:
    print("No faces detected!")

