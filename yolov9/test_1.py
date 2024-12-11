import cv2
import mediapipe as mp
import numpy as np
import math

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    refine_landmarks=True,
    max_num_faces=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Các điểm 3D cố định của mô hình khuôn mặt (ví dụ):
# Giá trị này bạn cần tự thiết lập dựa trên mô hình 3D cố định,
# ở đây là ví dụ (x,y,z) trong không gian 3D thật:
model_points = np.array([
    (0.0, 0.0, 0.0),             # Nose tip
    (0.0, -63.6, -12.0),         # Chin
    (-43.3, 32.7, -26.0),        # Left eye left corner
    (43.3, 32.7, -26.0),         # Right eye right corner
    (-28.0, -28.9, -24.1),       # Left Mouth corner
    (28.0, -28.9, -24.1)         # Right mouth corner
], dtype='double')

cap = cv2.VideoCapture(0)

pitch_calib, yaw_calib, roll_calib = 0,0,0
calibrated = False

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    h, w, _ = frame.shape
    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_image)
    
    if results.multi_face_landmarks:
        # Chọn khuôn mặt đầu tiên
        face_landmarks = results.multi_face_landmarks[0]
        
        # Lấy các landmark theo chỉ số tương ứng:
        # MediaPipe FaceMesh indexes: 
        # Nose tip: 1
        # Chin: 152
        # Left eye corner: 33 (hoặc 263 cho right eye corner)
        # v.v...
        
        image_points = np.array([
            (face_landmarks.landmark[1].x * w, face_landmarks.landmark[1].y * h),   # Nose tip
            (face_landmarks.landmark[152].x * w, face_landmarks.landmark[152].y * h), # Chin
            (face_landmarks.landmark[33].x * w, face_landmarks.landmark[33].y * h), # Left eye corner
            (face_landmarks.landmark[263].x * w, face_landmarks.landmark[263].y * h), # Right eye corner
            (face_landmarks.landmark[61].x * w, face_landmarks.landmark[61].y * h), # Left Mouth corner
            (face_landmarks.landmark[291].x * w, face_landmarks.landmark[291].y * h) # Right Mouth corner
        ], dtype='double')
        
        # Camera matrix giả sử (bạn cần điều chỉnh hoặc ước lượng tiêu cự)
        focal_length = w
        center = (w/2, h/2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]], dtype = "double"
        )
        
        # Giả sử distortion không đáng kể:
        dist_coeffs = np.zeros((4,1)) 
        
        # Giải bài toán PnP:
        success, rvec, tvec = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
        
        if success:
            # Chuyển rvec thành ma trận xoay
            R, _ = cv2.Rodrigues(rvec)
            
            sy = math.sqrt(R[0,0]*R[0,0] + R[1,0]*R[1,0])
            
            # Euler angles
            pitch = math.atan2(-R[2,0], sy)
            yaw = math.atan2(R[1,0], R[0,0])
            roll = math.atan2(R[2,1], R[2,2])
            
            if not calibrated:
                pitch_calib, yaw_calib, roll_calib = pitch, yaw, roll
                calibrated = True
            
            pitch_pred = pitch - pitch_calib
            yaw_pred = yaw - yaw_calib
            roll_pred = roll - roll_calib
            
            # Áp dụng logic
            if pitch_pred > 0.3:
                text = 'Top'
                if yaw_pred > 0.3:
                    text = 'Top Left'
                elif yaw_pred < -0.3:
                    text = 'Top Right'
            elif pitch_pred < -0.3:
                text = 'Bottom'
                if yaw_pred > 0.3:
                    text = 'Bottom Left'
                elif yaw_pred < -0.3:
                    text = 'Bottom Right'
            elif yaw_pred > 0.3:
                text = 'Left'
            elif yaw_pred < -0.3:
                text = 'Right'
            else:
                text = 'Forward'
            
            cv2.putText(frame, text, (50,50), cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
    
    cv2.imshow('Frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
