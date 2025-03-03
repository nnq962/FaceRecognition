import cv2
import numpy as np

ARUCO_DICT = {
	"DICT_4X4_50": cv2.aruco.DICT_4X4_50,
	"DICT_4X4_100": cv2.aruco.DICT_4X4_100,
	"DICT_4X4_250": cv2.aruco.DICT_4X4_250,
	"DICT_4X4_1000": cv2.aruco.DICT_4X4_1000,
	"DICT_5X5_50": cv2.aruco.DICT_5X5_50,
	"DICT_5X5_100": cv2.aruco.DICT_5X5_100,
	"DICT_5X5_250": cv2.aruco.DICT_5X5_250,
	"DICT_5X5_1000": cv2.aruco.DICT_5X5_1000,
	"DICT_6X6_50": cv2.aruco.DICT_6X6_50,
	"DICT_6X6_100": cv2.aruco.DICT_6X6_100,
	"DICT_6X6_250": cv2.aruco.DICT_6X6_250,
	"DICT_6X6_1000": cv2.aruco.DICT_6X6_1000,
	"DICT_7X7_50": cv2.aruco.DICT_7X7_50,
	"DICT_7X7_100": cv2.aruco.DICT_7X7_100,
	"DICT_7X7_250": cv2.aruco.DICT_7X7_250,
	"DICT_7X7_1000": cv2.aruco.DICT_7X7_1000,
	"DICT_ARUCO_ORIGINAL": cv2.aruco.DICT_ARUCO_ORIGINAL,
	"DICT_APRILTAG_16h5": cv2.aruco.DICT_APRILTAG_16h5,
	"DICT_APRILTAG_25h9": cv2.aruco.DICT_APRILTAG_25h9,
	"DICT_APRILTAG_36h10": cv2.aruco.DICT_APRILTAG_36h10,
	"DICT_APRILTAG_36h11": cv2.aruco.DICT_APRILTAG_36h11
}

def convert_angle_to_answer(angle):
    """
    Chuyển đổi góc từ 0 đến 360 độ thành đáp án A, B, C, D.
    
    - 45° → 135°   -> A
    - 135° → 225°  -> B
    - 225° → 315°  -> C
    - 315° → 45°   -> D
    """
    angle = angle % 360  # Đảm bảo góc trong khoảng 0-360

    if 45 <= angle < 135:
        return "A"
    elif 135 <= angle < 225:
        return "B"
    elif 225 <= angle < 315:
        return "C"
    else:  # Trường hợp còn lại: [315, 360) và [0, 45)
        return "D"


def aruco_display(corners, ids, rejected, image):
    marker_list = []
    
    if len(corners) > 0:
        ids = ids.flatten()
        
        for (markerCorner, markerID) in zip(corners, ids):
            # Lấy tọa độ 4 góc của marker
            corners = markerCorner.reshape((4, 2))
            (topLeft, topRight, bottomRight, bottomLeft) = corners
            
            # Chuyển đổi tọa độ sang số nguyên
            topLeft = (int(topLeft[0]), int(topLeft[1]))
            topRight = (int(topRight[0]), int(topRight[1]))
            bottomRight = (int(bottomRight[0]), int(bottomRight[1]))
            bottomLeft = (int(bottomLeft[0]), int(bottomLeft[1]))
            
            # Vẽ khung marker
            cv2.line(image, topLeft, topRight, (0, 255, 0), 2)
            cv2.line(image, topRight, bottomRight, (0, 255, 0), 2)
            cv2.line(image, bottomRight, bottomLeft, (0, 255, 0), 2)
            cv2.line(image, bottomLeft, topLeft, (0, 255, 0), 2)
            
            # Tính tâm marker
            cX = int((topLeft[0] + bottomRight[0]) / 2.0)
            cY = int((topLeft[1] + bottomRight[1]) / 2.0)
            cv2.circle(image, (cX, cY), 4, (0, 0, 255), -1)
            
            # ✅ Tính góc xoay của marker
            vector = np.array(topRight) - np.array(topLeft)  # Vector từ top-left đến top-right
            angle = np.degrees(np.arctan2(vector[1], vector[0]))  # Tính góc bằng arctan2
            if angle < 0:
                angle += 360  # Chuyển về khoảng [0, 360]
            
            # Hiển thị ID và góc xoay trên ảnh
            text = f"ID: {markerID}, Angle: {angle:.1f} deg"
            cv2.putText(image, text, (topLeft[0], topLeft[1] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Thêm thông tin vào danh sách
            marker_list.append({"ID": int(markerID), "Angle": round(angle, 1)})
    
    return image, marker_list

def detect_aruco_answers(corners, ids):
    """
    Nhận diện marker ArUco, tính toán góc xoay và ánh xạ thành đáp án A, B, C, D.
    
    - corners: Danh sách tọa độ các góc của marker.
    - ids: Danh sách ID của các marker.
    
    Trả về:
    - Danh sách chứa dictionary với ID và đáp án tương ứng.
    """
    marker_list = []

    if len(corners) > 0:
        ids = ids.flatten()

        for (markerCorner, markerID) in zip(corners, ids):
            # Lấy tọa độ 4 góc của marker
            corners = markerCorner.reshape((4, 2))
            (topLeft, topRight, bottomRight, bottomLeft) = corners

            # ✅ Tính góc xoay của marker
            vector = np.array(topRight) - np.array(topLeft)  # Vector từ top-left đến top-right
            angle = np.degrees(np.arctan2(vector[1], vector[0]))  # Tính góc bằng arctan2
            if angle < 0:
                angle += 360  # Chuyển về khoảng [0, 360]

            # Lưu kết quả dưới dạng {ID, Answer}
            marker_list.append({"ID": int(markerID), "Answer": convert_angle_to_answer(round(angle, 1))})
    
    return marker_list