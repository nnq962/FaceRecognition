import cv2
import numpy as np
from insightface.app.common import Face
from insightface.model_zoo import model_zoo
import os

# Khởi tạo model
model_path = os.path.expanduser("~/Models/det_10g.onnx")
det_model = model_zoo.get_model(model_path)
det_model.prepare(ctx_id=0, input_size=(640, 640), det_thres=0.5)

def draw_face_info(frame, bbox, kps, det_score):
    # Vẽ bounding box
    x1, y1, x2, y2 = map(int, bbox)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Vẽ keypoints với các màu khác nhau
    colors = [
        (255, 0, 0),   # Mắt trái - xanh dương
        (0, 0, 255),   # Mắt phải - đỏ
        (0, 255, 0),   # Mũi - xanh lá
        (255, 255, 0), # Góc miệng trái - vàng
        (255, 0, 255)  # Góc miệng phải - tím
    ]
    
    # Vẽ các điểm landmark
    for i, (x, y) in enumerate(kps):
        x, y = int(x), int(y)
        cv2.circle(frame, (x, y), 3, colors[i], -1)
    
    # Hiển thị detection score
    score_text = f"Score: {det_score:.2f}"
    cv2.putText(frame, score_text, (x1, y1-10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

def main():
    # Khởi tạo webcam
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Phát hiện khuôn mặt
        bboxes, kpss = det_model.detect(frame, max_num=0, metric='default')
        
        # Vẽ thông tin cho mỗi khuôn mặt được phát hiện
        if len(bboxes) > 0:
            for bbox, kps in zip(bboxes, kpss):
                det_score = bbox[4]
                bbox = bbox[:4]
                draw_face_info(frame, bbox, kps, det_score)
        
        # Hiển thị số lượng khuôn mặt
        cv2.putText(frame, f"Faces: {len(bboxes)}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Hiển thị frame
        cv2.imshow('Face Detection', frame)
        
        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Giải phóng tài nguyên
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()