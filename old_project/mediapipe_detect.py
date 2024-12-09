import cv2
import mediapipe as mp

class MediapipeDetector:
    def __init__(self):
        # Khởi tạo các đối tượng cần thiết từ mediapipe
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.detector = self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

    def detect_faces(self, frame):
        """
        Phát hiện khuôn mặt trong frame và trả về bounding boxes dưới dạng (x1, y1, x2, y2).
        :param frame: Ảnh từ camera (BGR format).
        :return: Danh sách các bounding box với tọa độ (x1, y1, x2, y2).
        """
        # Chuyển frame sang RGB vì mediapipe sử dụng RGB format
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Phát hiện khuôn mặt
        results = self.detector.process(image_rgb)

        # Danh sách chứa tọa độ các bounding box
        boxes = []

        if results.detections:
            for detection in results.detections:
                # Lấy tọa độ bounding box trong tỷ lệ với kích thước của ảnh
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape

                x1 = int(bboxC.xmin * iw)
                y1 = int(bboxC.ymin * ih)
                x2 = int((bboxC.xmin + bboxC.width) * iw)
                y2 = int((bboxC.ymin + bboxC.height) * ih)

                # Thêm tọa độ bounding box vào danh sách
                boxes.append((x1, y1, x2, y2))

        return boxes