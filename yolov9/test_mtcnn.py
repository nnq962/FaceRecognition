import cv2
import torch
from mtcnn import MTCNN as MTCNN1
from facenet_pytorch import MTCNN as MTCNN2
import time

# Kiểm tra thiết bị (sử dụng GPU nếu có)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Khởi tạo hai mô hình MTCNN
mtcnn_1 = MTCNN1()  # MTCNN từ mtcnn thư viện
mtcnn_2 = MTCNN2(keep_all=True, device=device)  # MTCNN từ facenet_pytorch

# Đọc ảnh và chuyển sang RGB
img = cv2.imread('assets/nnq1.jpeg')
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

start1 = time.time()
# Phát hiện khuôn mặt bằng MTCNN từ thư viện mtcnn
results_1 = mtcnn_1.detect_faces(img_rgb)
print("time process:", time.time() - start1)
print(results_1)

start2 = time.time()
# Phát hiện khuôn mặt bằng MTCNN từ thư viện facenet_pytorch
boxes_2, probs_2 = mtcnn_2.detect(img_rgb)
print("time process:", time.time() - start2)
print(probs_2)

# Vẽ kết quả từ MTCNN của thư viện mtcnn
if results_1:
    for result in results_1:
        x, y, width, height = result['box']
        cv2.rectangle(img, (x, y), (x + width, y + height), (0, 255, 0), 2)  # Màu xanh lá
        label = f"MTCNN1: {result['confidence']}"  # Không làm tròn xác suất
        cv2.putText(img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

# Vẽ kết quả từ MTCNN của thư viện facenet_pytorch
if boxes_2 is not None:
    for box, prob in zip(boxes_2, probs_2):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)  # Màu xanh dương
        label = f"MTCNN2: {prob}"  # Không làm tròn xác suất
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

# Hiển thị ảnh so sánh kết quả
cv2.imshow("Comparison: MTCNN (mtcnn) vs MTCNN (facenet_pytorch)", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
