import cv2

def process_image(image_path, detector):
    """
    Trích xuất embedding từ hình ảnh.

    Parameters:
        - image_path: Đường dẫn đến ảnh cần xử lý.
        - detector: Đối tượng chứa các hàm `get_face_detect` và `get_face_embedding`.

    Returns:
        - embedding: Mảng numpy chứa embedding của khuôn mặt (hoặc None nếu có lỗi).
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to read image {image_path}.")
        return None

    try:
        # Gọi hàm phát hiện khuôn mặt
        result = detector.get_face_detect(img)
        if not result or not result[0]:
            print(f"No face detected in {image_path}.")
            return None

        # Lấy tọa độ khuôn mặt đầu tiên
        face_box = result[0][0]

        # Trích xuất embedding
        embedding = detector.get_face_embedding(img, face_box[0], face_box[1], face_box[2])

        return embedding

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None