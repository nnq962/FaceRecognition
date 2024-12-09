from mtcnn import MTCNN

def get_mtcnn_detector():
    return MTCNN()

def check_single_face_quality(detector, image, bounding_box):
    """
    Kiểm tra chất lượng khuôn mặt dựa trên một bounding box và keypoints từ MTCNN.

    Args:
        detector (MTCNN): Đối tượng MTCNN detector.
        image (np.ndarray): Ảnh đầu vào (BGR).
        bounding_box (list): Bounding box ở dạng [x1, y1, x2, y2].

    Returns:
        dict: Kết quả kiểm tra gồm:
              - "is_valid" (bool): True nếu khuôn mặt đạt yêu cầu, ngược lại False.
              - "keypoints" (dict): Keypoints nếu phát hiện khuôn mặt, ngược lại None.
              - "error" (str): Thông báo lỗi nếu không hợp lệ (ví dụ: bounding box không hợp lệ).
    """
    h, w, _ = image.shape

    # Đảm bảo bounding box nằm trong kích thước ảnh
    x1 = max(0, bounding_box[0])
    y1 = max(0, bounding_box[1])
    x2 = min(w, bounding_box[2])
    y2 = min(h, bounding_box[3])

    # Kiểm tra bounding box có hợp lệ không
    if x1 >= x2 or y1 >= y2:
        return {"is_valid": False, "keypoints": None, "error": "Bounding box dimensions are invalid."}

    # Cắt ảnh dựa trên bounding box
    cropped_img = image[y1:y2, x1:x2]

    # Kiểm tra nếu ảnh bị lỗi
    if cropped_img.size == 0 or cropped_img.shape[0] == 0 or cropped_img.shape[1] == 0:
        return {"is_valid": False, "keypoints": None, "error": "Cropped image is invalid."}

    # Chạy MTCNN để kiểm tra keypoints
    detection = detector.detect_faces(cropped_img)

    if detection:
        keypoints = detection[0].get("keypoints", None)
        return {"is_valid": True, "keypoints": keypoints, "error": None}
    else:
        return {"is_valid": False, "keypoints": None, "error": "No face detected."}
