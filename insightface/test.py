import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)  # Mở camera

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Xử lý khung hình
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb_frame)

    if results.pose_landmarks:
        # Vẽ keypoints lên hình
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # Lấy tọa độ
        landmarks = results.pose_landmarks.landmark
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]

        if left_wrist.y < left_shoulder.y and left_elbow.y < left_shoulder.y:
            cv2.putText(frame, "Left Hand Raised", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow('Hand Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()