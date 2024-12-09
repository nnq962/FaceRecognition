import cv2
import numpy as np

prototxt_path = "ssd_weights/deploy.prototxt"
model_path = "ssd_weights/res10_300x300_ssd_iter_140000.caffemodel"

class SSDFaceDetectorOpenCV:
    def __init__(self, threshold=0.95):
        """
        Khởi tạo SSD face detector.
        :param threshold: Ngưỡng để quyết định khuôn mặt (mặc định là 0.5).
        """
        self.prototxt = prototxt_path
        self.model = model_path
        self.detector = cv2.dnn.readNetFromCaffe(self.prototxt, self.model)
        self.threshold = threshold

    def detect_faces(self, frame):
        """
        Phát hiện khuôn mặt trong một frame.
        :param frame: Khung hình từ camera.
        :return: Danh sách tọa độ các bounding box của khuôn mặt.
        """
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))

        self.detector.setInput(blob)
        detections = self.detector.forward()

        faces = []
        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]

            if confidence > self.threshold:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                faces.append(box.astype(int))

        return faces

    def extract_faces(self, frame):
        """
        Cắt các khuôn mặt từ frame dựa trên kết quả SSD detect.
        :param frame: Frame hình ảnh từ camera hoặc file.
        :return: Danh sách các khuôn mặt đã được cắt từ frame.
        """
        faces = self.detect_faces(frame)  # Gọi hàm detect_faces để lấy bounding boxes

        extracted_faces = []
        for box in faces:
            start_x, start_y, end_x, end_y = box

            # Cắt khuôn mặt từ frame
            face = frame[start_y:end_y, start_x:end_x]

            # Kiểm tra kích thước khuôn mặt (loại bỏ nếu quá nhỏ)
            if face.shape[0] > 0 and face.shape[1] > 0:
                extracted_faces.append(face)

        return extracted_faces

    def test_extract_faces(self, image_path):
        """
        Hàm test: load ảnh từ đường dẫn và hiển thị tất cả các khuôn mặt đã được cắt.
        :param image_path: Đường dẫn tới file hình ảnh.
        """
        # Đọc ảnh từ file
        frame = cv2.imread(image_path)
        
        # Extract faces
        faces = self.extract_faces(frame)
        print("so luong mat: ", len(faces))

        # Hiển thị từng khuôn mặt
        for i, face in enumerate(faces):
            cv2.imshow(f"Face {i+1}", face)
            cv2.waitKey(0)  # Nhấn phím bất kỳ để đóng cửa sổ ảnh

        # Đóng tất cả các cửa sổ ảnh
        cv2.destroyAllWindows()