import os
import gdown
from pathlib import Path
import numpy as np
import cv2
import pickle
import faiss

def prepare_models(model_urls, save_dir="~/Models"):
    """
    Kiểm tra và tải xuống các mô hình từ Google Drive nếu chưa tồn tại.

    Args:
        model_urls (dict): Từ điển chứa tên mô hình và URL Google Drive tương ứng.
                           Ví dụ: {"model1": "https://drive.google.com/uc?id=FILE_ID", ...}
    """
    # Chuẩn bị đường dẫn thư mục lưu trữ
    save_dir = os.path.expanduser(save_dir)
    os.makedirs(save_dir, exist_ok=True)

    for model_name, model_url in model_urls.items():
        # Đường dẫn lưu mô hình
        model_path = Path(save_dir) / model_name
        
        if model_path.exists():
            print(f"Model '{model_name}' already exists at '{model_path}'.")
        else:
            print(f"Downloading model '{model_name}' from '{model_url}' to '{model_path}'...")
            try:
                # Tải mô hình từ Google Drive
                gdown.download(model_url, str(model_path), quiet=False)
                print(f"Model '{model_name}' downloaded successfully!")
            except Exception as e:
                print(f"Failed to download model '{model_name}': {e}")

def crop_image(image, bbox):
    """
    Crop một vùng ảnh dựa trên bounding box.

    Args:
        image (numpy.ndarray): Ảnh đầu vào (đọc từ cv2.imread).
        bbox (numpy.ndarray or list): Bounding box 1D dạng float [x1, y1, x2, y2].

    Returns:
        numpy.ndarray: Ảnh đã crop.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("Input image must be a numpy array.")
    
    if not isinstance(bbox, (np.ndarray, list)) or len(bbox) != 4:
        raise ValueError("Bounding box must be a list or numpy array with 4 elements [x1, y1, x2, y2].")
    
    # Lấy tọa độ bounding box, chuyển thành số nguyên
    x1, y1, x2, y2 = map(int, bbox)

    # Đảm bảo tọa độ nằm trong phạm vi ảnh
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(image.shape[1], x2)
    y2 = min(image.shape[0], y2)

    # Crop ảnh
    cropped_image = image[y1:y2, x1:x2]

    return cropped_image

def expand_image(image, padding_size=50, padding_color=(0, 0, 0)):
    """
    Mở rộng toàn bộ ảnh bằng cách thêm viền xung quanh.

    Args:
        image (numpy.ndarray): Ảnh cần mở rộng.
        padding_size (int): Kích thước viền (số pixel) cần thêm ở mỗi cạnh.
        padding_color (tuple): Màu của viền (BGR format, default là màu đen).

    Returns:
        numpy.ndarray: Ảnh đã được mở rộng.
    """
    # Thêm padding bằng OpenCV
    expanded_image = cv2.copyMakeBorder(
        image,
        top=padding_size,
        bottom=padding_size,
        left=padding_size,
        right=padding_size,
        borderType=cv2.BORDER_CONSTANT,
        value=padding_color
    )
    return expanded_image

def is_small_face(bbox, min_size=50):
    """
    Kiểm tra xem khuôn mặt có kích thước nhỏ hơn ngưỡng cho phép hay không.

    Args:
        bbox (list or numpy.ndarray): Bounding box 1D ở dạng [x1, y1, x2, y2].
        min_size (int): Ngưỡng tối thiểu cho chiều rộng hoặc chiều cao (default: 50).

    Returns:
        bool: True nếu khuôn mặt là nhỏ, False nếu ngược lại.
    """
    if not isinstance(bbox, (list, np.ndarray)) or len(bbox) != 4:
        raise ValueError(f"Expected bbox to be a list or numpy array of length 4, got {type(bbox)} with shape {len(bbox)}")

    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1

    return width < min_size or height < min_size

def search_id(embedding, index_path="database/face_index.faiss", mapping_path="database/index_to_id.pkl", top_k=1, threshold=0.5):
    """
    Tìm kiếm ID và độ tương đồng trong cơ sở dữ liệu dựa trên một embedding, có ngưỡng độ tương đồng.

    Args:
        embedding (numpy.ndarray): Embedding đã chuẩn hóa (shape: (512,)).
        index_path (str): Đường dẫn tới FAISS index file.
        mapping_path (str): Đường dẫn tới file ánh xạ index -> ID.
        top_k (int): Số lượng kết quả gần nhất cần trả về.
        threshold (float): Ngưỡng độ tương đồng, loại bỏ kết quả có độ tương đồng thấp hơn ngưỡng.

    Returns:
        list of dict: Danh sách kết quả bao gồm ID, tên ảnh và độ tương đồng.
    """
    # Load FAISS index
    index = faiss.read_index(index_path)

    # Load ánh xạ index -> ID
    with open(mapping_path, "rb") as f:
        index_to_id = pickle.load(f)

    # Đảm bảo embedding là 2D để phù hợp với FAISS input
    query_embedding = np.array([embedding]).astype('float32')

    # Tìm kiếm với FAISS
    D, I = index.search(query_embedding, k=top_k)  # D: Độ tương đồng, I: Chỉ số

    results = []
    for i in range(top_k):
        idx = I[0][i]  # Chỉ số trong FAISS index
        similarity = D[0][i]
        if idx < 0 or similarity < threshold:  # Bỏ qua nếu không tìm thấy hoặc không đạt ngưỡng
            continue
        id_mapping = index_to_id[idx]
        results.append({
            "id": id_mapping["id"],
            "image": id_mapping["image"],
            "similarity": similarity
        })

    return results

model_urls = {
    "det_10g.onnx": "https://drive.google.com/uc?id=1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X",
    "w600k_r50.onnx": "https://drive.google.com/uc?id=1JKwOYResiJf7YyixHCizanYmvPrl1bP2",
    "GFPGANv1.3.pth": "https://drive.google.com/uc?id=1zmW9g7vaRWuFSUKIS9ShCmP-6WU6Xxan",
    "detection_Resnet50_Final.pth": "https://drive.google.com/uc?id=1jP3-UU8LhBvG8ArZQNl6kpDUfH_Xan9m",
    "parsing_parsenet.pth": "https://drive.google.com/uc?id=1ZFqra3Vs4i5fB6B8LkyBo_WQXaPRn77y"
}

prepare_models(model_urls=model_urls)