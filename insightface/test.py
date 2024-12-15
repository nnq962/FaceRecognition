import cv2
import numpy as np
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager

def expand_image(image, padding_size=50, padding_color=(0, 0, 0)):
    """
    Mở rộng toàn bộ ảnh bằng cách thêm viền xung quanh.

    Args:
        image (numpy.ndarray): Ảnh cần mở rộng.
        padding_size (int): Kích thước viền (số pixel) cần thêm ở mỗi cạnh.
        padding_color (tuple): Màu của viền (BGR format, default là màu đen).

    Returns:
        numpy.ndarray: Ảnh đã được mở rộng.
    """
    # Thêm padding bằng OpenCV
    expanded_image = cv2.copyMakeBorder(
        image,
        top=padding_size,
        bottom=padding_size,
        left=padding_size,
        right=padding_size,
        borderType=cv2.BORDER_CONSTANT,
        value=padding_color
    )
    return expanded_image

# Khởi tạo media manager và detector
media_manager = MediaManager(source='datatest/nnq1.jpg', nosave=False, face_recognition=True, face_emotion=True)
detector = InsightFaceDetector(media_manager=media_manager)

# Đọc ảnh debug_sharpen
img = cv2.imread("debug_sharpen.jpg")
if img is None:
    raise FileNotFoundError("Ảnh 'debug_sharpen.jpg' không tồn tại hoặc không thể đọc được.")

# Thêm padding cho ảnh
padding_size = 125  # Kích thước viền cần thêm
expanded_img = expand_image(img, padding_size=padding_size, padding_color=(0, 0, 0))

# Lưu ảnh đã mở rộng để kiểm tra
# cv2.imwrite("debug_sharpen_expanded.jpg", expanded_img)

# Phát hiện khuôn mặt trên ảnh mở rộng
rs = detector.get_face_detect(expanded_img)

# Hiển thị kết quả
print("Detection result after expanding image:", rs)

# Hiển thị ảnh trước và sau khi mở rộng
# cv2.imshow("Original Image", img)
cv2.imshow("Expanded Image", expanded_img)
cv2.waitKey(0)
cv2.destroyAllWindows()