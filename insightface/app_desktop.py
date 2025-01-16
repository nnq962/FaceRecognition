from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog
from desktop_app.main_window import Ui_MainWindow
from desktop_app.add_user_class import AddUserDialog
from desktop_app.add_image_class import AddImageDialog
from desktop_app.delete_image_class import DeleteImageDialog
from desktop_app.delete_user_class import DeleteUserDialog
from desktop_app.camera_window_class import CameraWindow  # Import cửa sổ camera
import cv2

class MainWindow(QMainWindow):
    """Cửa sổ chính quản lý các chức năng và mở camera"""
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Kết nối các nút với các chức năng
        self.ui.add_user_button.clicked.connect(self.open_add_user_dialog)
        self.ui.add_image_button.clicked.connect(self.open_add_image_dialog)
        self.ui.delete_image_button.clicked.connect(self.open_delete_image_dialog)
        self.ui.delete_user_button.clicked.connect(self.open_delete_user_dialog)

        # Bản đồ ID camera với URL RTSP
        self.camera_map = {
            "CAM001": "rtsp://192.168.1.142:8554/stream1",
            "CAM002": "rtsp://192.168.1.142:8554/stream2",
            "CAM003": "rtsp://192.168.1.142:8554/stream3",
        }

        # Danh sách các cửa sổ camera đã mở
        self.camera_windows = {}

        # Kết nối nút mở camera
        self.ui.open_camera_button.clicked.connect(self.open_camera)

    def open_camera(self):
        """Mở cửa sổ hiển thị video từ camera dựa trên ID"""
        camera_id = self.ui.cameraInput.text().strip()  # Lấy ID camera từ dòng nhập
        self.ui.cameraInput.clear()  # Xóa nội dung vừa nhập sau khi nhấn nút

        if camera_id in self.camera_map:
            rtsp_url = self.camera_map[camera_id]
            if camera_id not in self.camera_windows:
                # Kiểm tra nguồn stream
                capture = cv2.VideoCapture(rtsp_url)
                if not capture.isOpened():
                    print(f"Không thể kết nối tới nguồn stream: {rtsp_url}")
                    capture.release()
                    return  # Dừng nếu stream không khả dụng

                # Thông báo kết nối thành công
                print(f"Kết nối thành công tới camera: {camera_id} ({rtsp_url})")

                # Tạo cửa sổ mới nếu stream khả dụng
                camera_window = CameraWindow(camera_id, rtsp_url, self)
                self.camera_windows[camera_id] = camera_window
                camera_window.show()
            else:
                print(f"Camera {camera_id} đã được mở.")
        else:
            print(f"ID {camera_id} không hợp lệ. Vui lòng thử lại.")    

    # Các chức năng khác (thêm user, xóa user, v.v.)
    def open_add_user_dialog(self):
        dialog = AddUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            print(f"User data: {user_data}")

    def open_add_image_dialog(self):
        dialog = AddImageDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            print(f"Info {user_data}")

    def open_delete_image_dialog(self):
        dialog = DeleteImageDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            print(f"Info {user_data}")

    def open_delete_user_dialog(self):
        dialog = DeleteUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            user_data = dialog.get_user_data()
            print(f"Info {user_data}")

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())