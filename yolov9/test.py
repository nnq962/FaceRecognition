import cv2

# Mở webcam (0 là webcam mặc định)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Không thể mở webcam!")
    exit()

# Lấy độ phân giải của webcam
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))

print(f"Độ phân giải webcam: {width}x{height}")
print(f"Số khung hình mỗi giây (FPS): {fps}")

# Hiển thị video từ webcam
while True:
    ret, frame = cap.read()
    if not ret:
        print("Không thể nhận khung hình từ webcam!")
        break

    # Hiển thị video
    cv2.imshow("Webcam Video", frame)

    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng tài nguyên
cap.release()
cv2.destroyAllWindows()
