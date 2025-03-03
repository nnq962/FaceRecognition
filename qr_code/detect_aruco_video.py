import cv2
import argparse
import sys
from utils import ARUCO_DICT, aruco_display
import time

# Khởi tạo đối tượng phân tích tham số đầu vào
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--camera", required=True, help="Set to True if using webcam")
ap.add_argument("-v", "--video", help="Path to the video file")
ap.add_argument("-t", "--type", type=str, default="DICT_ARUCO_ORIGINAL", help="Type of ArUCo tag to detect")
args = vars(ap.parse_args())

# Xác định nguồn video (Webcam hoặc Video file)
if args["camera"].lower() == "true":
    video = cv2.VideoCapture(0)
    
else:
    if not args["video"]:
        print("[Error] Video file location is not provided")
        sys.exit(1)
    video = cv2.VideoCapture(args["video"])

# Kiểm tra loại ArUco marker hợp lệ
arucoDictType = ARUCO_DICT.get(args["type"], None)
if arucoDictType is None:
    print(f"[Error] ArUCo tag type '{args['type']}' is not supported")
    sys.exit(1)

# Khởi tạo ArUco detector
arucoDict = cv2.aruco.getPredefinedDictionary(arucoDictType)
arucoParams = cv2.aruco.DetectorParameters()
aruco_detector = cv2.aruco.ArucoDetector(arucoDict, arucoParams)

prev_time = time.time()

# Vòng lặp xử lý video
while True:
    ret, frame = video.read()
    if not ret:
        break  # Thoát khi không còn frame nào trong video

    # Phát hiện marker
    corners, ids, rejected = aruco_detector.detectMarkers(frame)
    detected_markers = aruco_display(corners, ids, rejected, frame)

    # Tính toán FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    # Hiển thị FPS trên frame
    cv2.putText(detected_markers, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Hiển thị kết quả
    cv2.imshow("ArUco Detection", detected_markers)

    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Giải phóng tài nguyên
video.release()
cv2.destroyAllWindows()