from PyQt5.QtWidgets import QDialog
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer
import cv2
from desktop_app.camera_window import Ui_Dialog  # Import giao diện

class CameraWindow(QDialog):
    """Cửa sổ con để hiển thị video từ một camera"""
    def __init__(self, camera_id, rtsp_url, parent):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.parent = parent  # Tham chiếu tới MainWindow để quản lý camera_windows
        self.setWindowTitle(f"Camera {camera_id}")

        # Kết nối tới camera
        self.capture = cv2.VideoCapture(rtsp_url)

        # Tạo timer để cập nhật video
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        """Cập nhật và hiển thị frame từ camera"""
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = frame.shape
            bytes_per_line = channel * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            self.ui.videoLabel.setPixmap(pixmap)

    def closeEvent(self, event):
        """Giải phóng tài nguyên khi đóng cửa sổ"""
        self.capture.release()
        self.timer.stop()
        # Xóa ID camera khỏi danh sách khi đóng
        self.parent.camera_windows.pop(self.camera_id, None)