import cv2
import ssd_detect
import mtcnn_detect
import mediapipe_detect

class CameraManager:
    def __init__(self, camera_id=0, frame_width=640, frame_height=480, detector=None):
        """
        Khởi tạo camera manager với các thông số camera.
        :param camera_id: ID của camera hoặc URL stream.
        :param frame_width: Chiều rộng khung hình (mặc định 640).
        :param frame_height: Chiều cao khung hình (mặc định 480).
        """
        # Kiểm tra nếu `camera_id` là URL stream (RTSP/HTTP) hay ID webcam
        self.is_stream = isinstance(camera_id, str) and (camera_id.startswith("rtsp://") or camera_id.startswith("http://"))
        
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise ValueError("Cannot open camera")

        # Với webcam, thiết lập kích thước trực tiếp
        if not self.is_stream:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
        
        # Các biến frame width và frame height sẽ được dùng cho resize sau khi đọc stream
        self.frame_width = frame_width
        self.frame_height = frame_height

        # Xác định detector
        if detector is None or detector == 'ssd':
            self.face_detection = ssd_detect.SSDFaceDetectorOpenCV()
        elif detector == 'mediapipe':
            self.face_detection = mediapipe_detect.MediapipeDetector()
        elif detector == 'mtcnn':
            self.face_detection = mtcnn_detect.MTCNNFaceDetector()
        else:
            raise ValueError("Unknown detector type")

        print("===================", detector, "===================")

    def get_frame(self, flip_code=None):
        """
        Lấy khung hình từ camera và điều chỉnh kích thước nếu cần.
        """
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Không thể đọc từ camera.")

        # Resize nếu là stream để đảm bảo kích thước khung hình đúng
        if self.is_stream:
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))

        if flip_code is not None:
            frame = cv2.flip(frame, flip_code)
        
        return frame

    def detect_faces(self, frame):
        """
        Phát hiện khuôn mặt trong một frame bằng MTCNN.
        :param frame: Frame từ camera.
        :return: Danh sách tọa độ các bounding box của khuôn mặt.
        """
        return self.face_detection.detect_faces(frame)

    @staticmethod
    def draw_faces(frame, boxes, names, emotions):
        """
        Vẽ các bounding box khuôn mặt lên frame và thêm tên người cùng cảm xúc.
        :param frame: Frame từ camera.
        :param boxes: Danh sách tọa độ các bounding box khuôn mặt.
        :param names: Danh sách tên tương ứng với các khuôn mặt.
        :param emotions: Danh sách cảm xúc tương ứng với các khuôn mặt.
        :return: Frame với bounding box khuôn mặt, tên người và cảm xúc.
        """

        if boxes is None or len(boxes) == 0:
            return frame  # Nếu không có khuôn mặt nào thì trả về frame ban đầu

        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = [int(b) for b in box]

            # Vẽ bounding box quanh khuôn mặt
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

            # Gắn tên và cảm xúc lên bounding box
            name = names[i] if i < len(names) else "Unknown"
            emotion = emotions[i] if i < len(emotions) else "Unknown"
            label = f"{name} | {emotion}"

            font_scale = 0.7
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(frame, label, (x1, y1 - 10), font, font_scale, (0, 0, 255), 1)

        return frame

    def release(self):
        """
        Giải phóng camera.
        """
        self.cap.release()
        cv2.destroyAllWindows()
