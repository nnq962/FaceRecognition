import cv2

# Thử mở webcam ở index 0
cap = cv2.VideoCapture(0)

if cap.isOpened():
    print("✅ Webcam index 0 đang hoạt động.")
else:
    print("❌ Không tìm thấy webcam ở index 0.")

cap.release()
