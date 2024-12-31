import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5)

def is_person_raising_hand_image(image_bgr):
    """
    Kiểm tra xem người trong ảnh (frame) có đang giơ tay hay không.
    - Chỉ cần MỘT trong hai tay (trái/phải) giơ lên (wrist.y < shoulder.y) thì hàm trả về True.
    - Trả về False nếu không phát hiện người, hoặc không có tay nào giơ lên.
    
    Tham số:
      image_bgr: ảnh BGR (thường đọc từ cv2.imread hoặc camera)
    
    Trả về:
      True  - nếu phát hiện người và có ít nhất 1 tay giơ lên
      False - nếu không phát hiện người, hoặc người không giơ tay
    """

    # Chuyển ảnh sang RGB cho MediaPipe
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # Tạo một đối tượng pose cho ảnh tĩnh (static_image_mode=True)

    results = pose.process(image_rgb)

    # Nếu không phát hiện pose, trả về False
    if not results.pose_landmarks:
        return False

    # Lấy landmark vai (shoulder) và cổ tay (wrist) bên trái/phải
    # Theo MediaPipe Pose: 
    #   Landmark 11: Left Shoulder,  12: Right Shoulder
    #   Landmark 15: Left Wrist,     16: Right Wrist
    left_shoulder  = results.pose_landmarks.landmark[11]
    right_shoulder = results.pose_landmarks.landmark[12]
    left_wrist     = results.pose_landmarks.landmark[15]
    right_wrist    = results.pose_landmarks.landmark[16]

    # Kiểm tra tay trái giơ lên:
    # (tay trái giơ lên nếu y của cổ tay < y của vai trái)
    left_hand_raised = (left_wrist.y < left_shoulder.y)

    # Kiểm tra tay phải giơ lên:
    # (tay phải giơ lên nếu y của cổ tay < y của vai phải)
    right_hand_raised = (right_wrist.y < right_shoulder.y)

    # Nếu 1 trong 2 tay giơ => trả về True
    if left_hand_raised or right_hand_raised:
        return True
    else:
        return False


def main():
    cap = cv2.VideoCapture(0)
    while True:
        success, image = cap.read()
        if not success:
            print("Không thể đọc từ webcam!")
            break

        # Kiểm tra xem bàn tay này đang mở hay không
        if is_person_raising_hand(image):
            text_status = f"Hand is fully opened"
        else:
            text_status = f"Hand is NOT fully opened"

        print(text_status)

        cv2.imshow("Hand Detection", image)
        
        if cv2.waitKey(1) & 0xFF == 27:  # ESC để thoát
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()