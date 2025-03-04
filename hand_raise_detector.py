import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, max_num_hands=2, min_detection_confidence=0.5)

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=True, model_complexity=1, enable_segmentation=False, min_detection_confidence=0.5)

def expand_and_crop_image(image, bbox, left=0.2, right=0.2, top=0.4, bottom=0.4):
    """
    Mở rộng bounding box theo 4 hướng riêng biệt (trái, phải, trên, dưới)
    và cắt ảnh theo bounding box đã mở rộng.

    Tham số:
      - image: Ảnh đã load bằng cv2.imread (dạng numpy array).
      - bbox: Bounding box dạng (x_min, y_min, x_max, y_max).
      - left: Tỷ lệ mở rộng phía trái.
      - right: Tỷ lệ mở rộng phía phải.
      - top: Tỷ lệ mở rộng phía trên.
      - bottom: Tỷ lệ mở rộng phía dưới.
    
    Trả về:
      - Cropped image: Ảnh được cắt theo bounding box mở rộng.
    """
    x_min, y_min, x_max, y_max = bbox
    height, width = image.shape[:2]

    # Kích thước ban đầu của bounding box
    w = x_max - x_min
    h = y_max - y_min

    # Tính toán bounding box mở rộng theo 4 hướng riêng biệt
    new_x_min = max(0, int(x_min - left * w))          # Mở rộng trái
    new_y_min = max(0, int(y_min - top * h))           # Mở rộng trên
    new_x_max = min(width, int(x_max + right * w))     # Mở rộng phải
    new_y_max = min(height, int(y_max + bottom * h))   # Mở rộng dưới

    # Cắt ảnh theo bounding box mở rộng
    cropped_image = image[new_y_min:new_y_max, new_x_min:new_x_max]

    return cropped_image

def is_finger_extended(hand_landmarks, finger_indices):
    """
    Hàm kiểm tra xem một ngón tay có duỗi thẳng hay không
    bằng cách so sánh toạ độ y giữa các đốt.
    finger_indices gồm 4 chỉ số landmark của ngón (MCP, PIP, DIP, TIP).
    """
    mcp_id, pip_id, dip_id, tip_id = finger_indices

    mcp_y = hand_landmarks.landmark[mcp_id].y
    pip_y = hand_landmarks.landmark[pip_id].y
    dip_y = hand_landmarks.landmark[dip_id].y
    tip_y = hand_landmarks.landmark[tip_id].y
    
    # Logic demo: TIP y < PIP y, DIP y, MCP y => ngón duỗi (giả định tay đưa thẳng, camera trước mặt)
    return (tip_y < pip_y and tip_y < dip_y and tip_y < mcp_y)

def is_hand_opened(hand_landmarks):
    """
    Kiểm tra bàn tay có đang mở (tất cả ngón tay duỗi thẳng) hay không.
    Trả về True nếu tất cả 5 ngón duỗi thẳng, False nếu ngược lại.
    """
    # Định nghĩa index cho từng ngón tay (MCP, PIP, DIP, TIP)
    thumb_indices  = (1, 2, 3, 4)     # ngón cái
    index_indices  = (5, 6, 7, 8)     # ngón trỏ
    middle_indices = (9, 10, 11, 12)  # ngón giữa
    ring_indices   = (13, 14, 15, 16) # ngón áp út
    pinky_indices  = (17, 18, 19, 20) # ngón út

    thumb_extended  = is_finger_extended(hand_landmarks, thumb_indices)
    index_extended  = is_finger_extended(hand_landmarks, index_indices)
    middle_extended = is_finger_extended(hand_landmarks, middle_indices)
    ring_extended   = is_finger_extended(hand_landmarks, ring_indices)
    pinky_extended  = is_finger_extended(hand_landmarks, pinky_indices)
    
    # Kiểm tra tất cả đều True
    return (thumb_extended and index_extended and 
            middle_extended and ring_extended and 
            pinky_extended)

def is_hand_opened_in_image(image):
    """
    Trả về True nếu phát hiện bàn tay trong ảnh và tất cả ngón tay duỗi,
    ngược lại trả về False.
    
    Tham số:
      - image: ảnh BGR (đã load bằng cv2.imread)
    """
    # Chuyển ảnh sang RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Phát hiện bàn tay
    results = hands.process(image_rgb)
    
    # Nếu tìm thấy bàn tay
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Kiểm tra xem bàn tay này có mở không
            if is_hand_opened(hand_landmarks):
                return True
    return False
    
def is_person_raising_hand_image(image):
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
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

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
    
def get_raising_hand(frame, bbox):
    """
    Kiểm tra xem người trong bounding box có giơ tay không.

    Args:
        frame (numpy.ndarray): Ảnh gốc.
        bbox (list): Bounding box của người (x1, y1, x2, y2).

    Returns:
        dict: Trả về dict chứa trạng thái tay (luôn luôn trả về, không phụ thuộc vào thay đổi trạng thái).
    """
    cropped_expand_image = expand_and_crop_image(
        frame, bbox, left=2.8, right=2.8, top=4.6, bottom=1.6
    )

    hand_open = is_hand_opened_in_image(cropped_expand_image)
    hand_raised = is_person_raising_hand_image(cropped_expand_image)
    if hand_open and hand_raised:
        return True
    
    return False