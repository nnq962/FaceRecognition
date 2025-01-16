import cv2

# Địa chỉ RTSP
rtsp_url = "rtsp://admin:Admin123@192.168.1.80:554/Streaming/Channels/301"

# Kết nối tới RTSP
cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("Không thể kết nối đến luồng RTSP. Kiểm tra lại địa chỉ!")
else:
    print("Đang hiển thị video...")

# Hiển thị video
while True:
    ret, frame = cap.read()
    if not ret:
        print("Không nhận được khung hình. Kiểm tra kết nối RTSP.")
        break

    # Hiển thị khung hình
    cv2.imshow("RTSP Stream", frame)

    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()