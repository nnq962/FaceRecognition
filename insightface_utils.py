import os
import gdown
from pathlib import Path
import numpy as np
import cv2
import pickle
from insightface.utils import face_align
# from deepface import DeepFace
import platform
import faiss
from config import config

users_collection = config.users_collection
save_path = config.save_path

# Detect the operating system
current_os = platform.system()

if current_os == "Darwin":  # macOS
    faiss.omp_set_num_threads(1)  # Limit FAISS to use 1 thread
elif current_os == "Linux":
    # Skip setting omp_set_num_threads
    pass

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


model_urls = {
    "det_10g.onnx": "https://drive.google.com/uc?id=1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X",
    "w600k_r50.onnx": "https://drive.google.com/uc?id=1JKwOYResiJf7YyixHCizanYmvPrl1bP2",
    "GFPGANv1.3.pth": "https://drive.google.com/uc?id=1zmW9g7vaRWuFSUKIS9ShCmP-6WU6Xxan",
    "detection_Resnet50_Final.pth": "https://drive.google.com/uc?id=1jP3-UU8LhBvG8ArZQNl6kpDUfH_Xan9m",
    "parsing_parsenet.pth": "https://drive.google.com/uc?id=1ZFqra3Vs4i5fB6B8LkyBo_WQXaPRn77y"
}

prepare_models(model_urls=model_urls)

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

def search_ids(embeddings, index_path="data_base/face_index.faiss", mapping_path="data_base/index_to_id.pkl", top_k=1, threshold=0.5):
    """
    Tìm kiếm ID và độ tương đồng trong cơ sở dữ liệu dựa trên một mảng embeddings, với ngưỡng độ tương đồng.

    Args:
        embeddings (numpy.ndarray): Mảng các embeddings đã chuẩn hóa (shape: (n_embeddings, 512)).
        index_path (str): Đường dẫn tới FAISS index file.
        mapping_path (str): Đường dẫn tới file ánh xạ index -> ID.
        top_k (int): Số lượng kết quả gần nhất cần trả về cho mỗi embedding.
        threshold (float): Ngưỡng độ tương đồng, loại bỏ kết quả có độ tương đồng thấp hơn ngưỡng.

    Returns:
        list of list of dict: Danh sách kết quả cho mỗi embedding, mỗi kết quả bao gồm ID, tên ảnh và độ tương đồng.
    """
    # Load FAISS index
    index = faiss.read_index(index_path)

    # Load ánh xạ index -> ID
    with open(mapping_path, "rb") as f:
        index_to_id = pickle.load(f)

    # Đảm bảo embeddings là 2D để phù hợp với FAISS input
    query_embeddings = np.array(embeddings).astype('float32')

    # Tìm kiếm với FAISS
    D, I = index.search(query_embeddings, k=top_k)  # D: Độ tương đồng, I: Chỉ số

    all_results = []  # Kết quả cho tất cả embeddings
    for query_idx, (distances, indices) in enumerate(zip(D, I)):
        query_results = []
        for i in range(top_k):
            idx = indices[i]  # Chỉ số trong FAISS index
            similarity = distances[i]
            if idx < 0 or similarity < threshold:  # Bỏ qua nếu không tìm thấy hoặc không đạt ngưỡng
                continue
            id_mapping = index_to_id[idx]
            query_results.append({
                "id": id_mapping["id"],
                "image": id_mapping["image"],
                "similarity": similarity
            })
        all_results.append(query_results)

    return all_results

def search_ids_mongoDB(embeddings, index_path=save_path + "/data_base/face_index.faiss", top_k=1, threshold=0.5):
    """
    Tìm kiếm ID và độ tương đồng trong cơ sở dữ liệu MongoDB dựa trên một mảng embeddings, với ngưỡng độ tương đồng.

    Args:
        embeddings (numpy.ndarray): Mảng các embeddings đã chuẩn hóa (shape: (n_embeddings, 512)).
        index_path (str): Đường dẫn tới FAISS index file.
        top_k (int): Số lượng kết quả gần nhất cần trả về cho mỗi embedding.
        threshold (float): Ngưỡng độ tương đồng, loại bỏ kết quả có độ tương đồng thấp hơn ngưỡng.

    Returns:
        list of list of dict: Danh sách kết quả cho mỗi embedding, mỗi kết quả bao gồm ID, tên ảnh và độ tương đồng.
    """
    # Kiểm tra tệp FAISS index
    if not os.path.exists(index_path):
        print(f"FAISS index file không tồn tại tại: {index_path}")
        return []

    # Load FAISS index
    index = faiss.read_index(index_path)

    # Đảm bảo embeddings là 2D để phù hợp với FAISS input
    query_embeddings = np.array(embeddings).astype('float32')

    # Tìm kiếm với FAISS
    D, I = index.search(query_embeddings, k=top_k)  # D: Độ tương đồng, I: Chỉ số

    # Kết quả cho tất cả embeddings
    all_results = []
    for distances, indices in zip(D, I):
        query_results = []
        for idx, similarity in zip(indices, distances):
            if idx < 0 or similarity < threshold:  # Bỏ qua nếu không tìm thấy hoặc không đạt ngưỡng
                continue

            # Truy vấn MongoDB để lấy thông tin người dùng
            user = users_collection.find_one({"_id": int(idx)})
            if user:
                query_results.append({
                    "id": user["_id"],
                    "full_name": user["full_name"],
                    "similarity": similarity
                })
        all_results.append(query_results)

    return all_results

def crop_and_align_faces(img, bboxes, keypoints, conf_threshold=0.5, image_size=112):
    """
    Cắt và chuẩn hóa các khuôn mặt từ ảnh gốc dựa trên bounding boxes và keypoints.
    
    Args:
        img (numpy.ndarray): Ảnh gốc.
        bboxes (numpy.ndarray): Bounding boxes, mỗi box có định dạng [x1, y1, x2, y2, conf].
        keypoints (numpy.ndarray): Landmarks (keypoints) của khuôn mặt.
        conf_threshold (float): Ngưỡng độ tin cậy (confidence) để lọc khuôn mặt.
        image_size (int): Kích thước ảnh sau khi chuẩn hóa (ví dụ: 112x112).
        
    Returns:
        list: Danh sách các ảnh khuôn mặt đã cắt và chuẩn hóa.
    """
    cropped_faces = []

    for bbox, kps in zip(bboxes, keypoints):
        if bbox[4] >= conf_threshold:
            cropped_face = face_align.norm_crop(img, landmark=kps, image_size=image_size)
            cropped_faces.append(cropped_face)
    
    return cropped_faces

def normalize_embeddings(embeddings):
    """
    Chuẩn hóa danh sách các embedding.

    Args:
        embeddings (numpy.ndarray): Mảng các embedding (shape: n_faces x embedding_dim).

    Returns:
        numpy.ndarray: Mảng các embedding đã chuẩn hóa (cùng shape với đầu vào).
    """
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.maximum(norms, 1e-8)  # Tránh chia cho 0

def save_data_to_mongo(data):
    """
    Hàm lưu dữ liệu vào MongoDB.

    Parameters:
        data (dict or list): Dữ liệu cần lưu, có thể là một tài liệu hoặc danh sách tài liệu.
        db_name (str): Tên cơ sở dữ liệu.
        collection_name (str): Tên collection.
        mongo_url (str): Chuỗi kết nối MongoDB.

    Returns:
        dict: Thông tin phản hồi sau khi chèn dữ liệu.
    """
    try:
        # Lưu dữ liệu
        if isinstance(data, list):
            result = config.data_collection.insert_many(data)
            return {"status": "success", "inserted_ids": result.inserted_ids}
        elif isinstance(data, dict):
            result = config.data_collection.insert_one(data)
            return {"status": "success", "inserted_id": result.inserted_id}
        else:
            return {"status": "error", "message": "Data must be a dictionary or a list of dictionaries"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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

# def is_real_face(img, threshold=0.65):
#     """
#     Check if a face in the image is real based on the anti-spoofing score.

#     Args:
#         img (str or numpy.ndarray): Path to the image or image data.
#         threshold (float): Threshold to determine if the face is real.

#     Returns:
#         list: [True, antispoof_score] if the score exceeds the threshold; 
#               [False, antispoof_score] otherwise.
#     """
#     try:
#         # Call extract_faces with anti-spoofing enabled
#         result = DeepFace.extract_faces(img_path=img, anti_spoofing=True, detector_backend='skip')

#         # Check the result
#         antispoof_score = result[0].get('antispoof_score', None)
#         if antispoof_score is not None:
#             # Return the result as a list
#             return [antispoof_score > threshold, antispoof_score]
#         else:
#             print("antispoof_score not found.")
#             return [False, None]
#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         return [False, None]