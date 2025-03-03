import cv2
import numpy as np

# Kiểm tra phiên bản OpenCV
print("OpenCV version:", cv2.__version__)

# Số lượng marker cần tạo
num_markers = 1  # Bạn có thể thay đổi số lượng marker muốn tạo
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)

# Kích thước mỗi marker (pixel)
marker_size = 200  

# Số cột và hàng để sắp xếp marker
cols = 5  # Số cột marker trên ảnh
rows = (num_markers + cols - 1) // cols  # Tính số hàng dựa trên số marker

# Khoảng cách giữa các marker
spacing = 20  

# Kích thước ảnh tổng hợp
image_width = cols * (marker_size + spacing) - spacing
image_height = rows * (marker_size + spacing) - spacing

# Tạo ảnh nền trắng (mức xám)
output_image = np.ones((image_height, image_width), dtype=np.uint8) * 255

# Vẽ từng marker lên ảnh sử dụng generateImageMarker
for i in range(num_markers):
    marker_id = i  # ID của marker
    # Tạo ảnh marker với shape (marker_size, marker_size, 1)
    marker_img = np.zeros((marker_size, marker_size, 1), dtype="uint8")
    
    # Sử dụng generateImageMarker để vẽ marker
    cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size, marker_img, 1)
    
    # Nếu cần chuyển về 2 chiều (loại bỏ kênh thứ 3) để ghép vào ảnh nền
    marker_img = marker_img[:, :, 0]
    
    # Tính vị trí đặt marker trên ảnh lớn
    row_idx = i // cols
    col_idx = i % cols
    y = row_idx * (marker_size + spacing)
    x = col_idx * (marker_size + spacing)

    output_image[y:y + marker_size, x:x + marker_size] = marker_img

# Lưu ảnh ra file
cv2.imwrite("tags/aruco_markers.png", output_image)

# Hiển thị ảnh kết quả
cv2.imshow("Generated ArUco Markers", output_image)
cv2.waitKey(0)
cv2.destroyAllWindows()