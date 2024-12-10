import cv2
import torch
from facenet_pytorch import MTCNN

# Kiểm tra GPU và khởi tạo MTCNN
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(keep_all=True, device=device)

# Mở webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Không thể mở webcam!")
else:
    # Thiết lập MJPG để đạt FPS cao
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    # Thiết lập độ phân giải và FPS
    desired_width = 2560
    desired_height = 1440
    desired_fps = 30

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, desired_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, desired_height)
    cap.set(cv2.CAP_PROP_FPS, desired_fps)

    # Kiểm tra lại thông số thực tế
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"Đã thiết lập webcam: {width}x{height} @ {fps} FPS")

    # Thiết lập VideoWriter để lưu video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec MP4
    out = cv2.VideoWriter('output.mp4', fourcc, fps, (width, height))

    print("Đang lưu video vào 'output.mp4'...")

    # Tỉ lệ thu nhỏ hiển thị
    scale_percent = 50  # Thu nhỏ 50%
    display_width = int(width * scale_percent / 100)
    display_height = int(height * scale_percent / 100)

    # Hiển thị và lưu video
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Không thể nhận khung hình từ webcam!")
            break

        # Chuyển đổi BGR -> RGB cho MTCNN
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Dùng MTCNN để phát hiện khuôn mặt
        boxes, probs, landmarks = mtcnn.detect(rgb_frame, landmarks=True)

        # Vẽ bounding boxes và keypoints nếu có khuôn mặt
        if boxes is not None:
            for box, prob, landmark in zip(boxes, probs, landmarks):
                # Vẽ bounding box
                x1, y1, x2, y2 = map(int, box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Xanh lá

                # Hiển thị xác suất
                label = f"{prob:.2f}"
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Vẽ keypoints
                for x, y in landmark:
                    cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)  # Đỏ

        # Ghi khung hình vào file video
        out.write(frame)

        # Thu nhỏ khung hình để hiển thị
        display_frame = cv2.resize(frame, (display_width, display_height))

        # Hiển thị video đã thu nhỏ
        cv2.imshow("Webcam with Face Detection", display_frame)

        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("Video đã được lưu.")
