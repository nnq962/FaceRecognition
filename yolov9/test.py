import cv2

# Mở video (thay thế 0 bằng đường dẫn video nếu cần)
video_path = "path/to/video.mp4"
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Không thể mở video!")
else:
    # Đặt độ phân giải mong muốn nếu biết trước
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3072)  # Thay thế bằng độ rộng bạn muốn
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1400)  # Thay thế bằng chiều cao bạn muốn

    # Lấy lại độ phân giải và FPS
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"Độ phân giải: {width} x {height}")
    print(f"FPS: {fps}")

    # Đọc và hiển thị video
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Hiển thị video
        cv2.imshow("Video", frame)

        # Nhấn 'q' để thoát
        if cv2.waitKey(int(1000 / fps)) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
