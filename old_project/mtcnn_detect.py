import cv2
from mtcnn import MTCNN

class MTCNNFaceDetector:
    def __init__(self):
        self.detector = MTCNN()

    def detect_faces(self, frame):
        """
        Phát hiện khuôn mặt và trả về danh sách tọa độ dạng x1, y1, x2, y2.
        :param frame: Frame đầu vào từ camera.
        :return: Danh sách các bounding box [(x1, y1, x2, y2), ...].
        """
        # Chuyển đổi frame từ BGR sang RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Phát hiện khuôn mặt bằng MTCNN
        faces = self.detector.detect_faces(image_rgb)

        # Tạo danh sách bounding box với định dạng x1, y1, x2, y2
        boxes = []
        for face in faces:
            x, y, width, height = face['box']
            x1, y1 = x, y
            x2, y2 = x + width, y + height
            boxes.append([x1, y1, x2, y2])

        return boxes
