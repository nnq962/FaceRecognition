from fer import FER
import numpy as np

detector = FER()

def xyxy2xywh(boxes):
    """
    Args:
        boxes (list of lists): Danh sách các bounding boxes, mỗi box ở dạng [x1, y1, x2, y2].
    Returns:
        list of lists: Danh sách bounding boxes đã chuyển đổi sang [x1, y1, w, h].
    """
    return np.array([[x1, y1, x2 - x1, y2 - y1] for x1, y1, x2, y2 in boxes])


def analyze_face(img, face_rectangles):
    return detector.detect_emotions(img, xyxy2xywh(face_rectangles))


def get_dominant_emotion(results):
    dominant_emotions = []
    for face in results:
        if face['emotions']:
            # Lấy cảm xúc có xác suất cao nhất
            dominant_emotion = max(face['emotions'], key=face['emotions'].get)
            probability = round(face['emotions'][dominant_emotion], 2)  # Làm tròn 2 chữ số
            dominant_emotions.append([dominant_emotion, probability])
        else:
            dominant_emotions.append([None, 0.0])  # Không có cảm xúc được phát hiện
    return dominant_emotions