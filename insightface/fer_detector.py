from fer import FER
import numpy as np

detector = FER()

def xyxy2xywh(boxes):
    if not isinstance(boxes, np.ndarray):
        raise TypeError(f"Expected input to be a numpy.ndarray, got {type(boxes)}")

    if boxes.ndim == 1:  # Trường hợp 1D: Một bounding box
        if boxes.shape[0] != 4:
            raise ValueError(f"Expected input shape to be [4], got {boxes.shape}")
        x1, y1, x2, y2 = boxes
        w = x2 - x1
        h = y2 - y1
        return np.array([int(x1), int(y1), int(w), int(h)], dtype=np.int32)

    elif boxes.ndim == 2:  # Trường hợp 2D: Nhiều bounding boxes
        if boxes.shape[1] != 4:
            raise ValueError(f"Expected input shape to be [N, 4], got {boxes.shape}")
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        w = x2 - x1
        h = y2 - y1
        return np.stack((x1, y1, w, h), axis=1).astype(np.int32)

    else:
        raise ValueError(f"Expected input to have 1 or 2 dimensions, got {boxes.ndim}")

def analyze_face(img, face_rectangles):
    return detector.detect_emotions(img, [xyxy2xywh(face_rectangles)])

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