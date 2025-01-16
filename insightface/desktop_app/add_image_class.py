from PyQt5.QtWidgets import QDialog
from desktop_app.add_image import Ui_Dialog  # Import giao diện từ add_user.py

class AddImageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # Kết nối nút OK và Cancel
        self.ui.OK_Button.clicked.connect(self.accept)  # Xác nhận
        self.ui.Cancel_Button.clicked.connect(self.reject)  # Hủy bỏ

    def get_user_data(self):
        """Lấy dữ liệu nhập vào từ các trường"""
        return {
            "username": self.ui.username.text(),
            "password": self.ui.password.text(),
            "image_path": self.ui.image_path.text(),
        }