import os
import faiss
from config import config
import cv2
from annoy import AnnoyIndex
import numpy as np

users_collection = config.users_collection
save_path = config.save_path

def search_annoy(query_embedding, n_neighbors=1, threshold=None):
    """
    Tìm kiếm trong Annoy index sử dụng Euclidean Distance, và chuyển đổi về Cosine Similarity để so sánh với ngưỡng.

    Parameters:
        - query_embedding: Numpy array chứa vector cần tìm kiếm (đã chuẩn hóa trước).
        - n_neighbors: Số lượng hàng xóm gần nhất cần tìm.
        - threshold: Ngưỡng Cosine Similarity tối thiểu (nếu None, không áp dụng).

    Returns:
        - Danh sách các user_id và ảnh gần nhất, có lọc theo threshold nếu cần.
    """

    # Kiểm tra file tồn tại trước khi load
    if not os.path.exists(config.ann_file):
        print(f"Missing Annoy index file: {config.ann_file}")
        return []

    if not os.path.exists(config.mapping_file):
        print(f"Missing mapping file: {config.mapping_file}")
        return []

    # Load Annoy Index (sử dụng Euclidean thay vì Angular)
    annoy_index = AnnoyIndex(config.vector_dim, 'euclidean')
    annoy_index.load(config.ann_file)

    # Load Mapping từ file .npy
    id_mapping = np.load(config.mapping_file, allow_pickle=True).item()

    # Tìm n_neighbors gần nhất từ Annoy index
    indices, distances = annoy_index.get_nns_by_vector(query_embedding, n_neighbors, include_distances=True)

    # Chuyển đổi toàn bộ khoảng cách Euclidean sang Cosine Similarity bằng NumPy (Nhanh hơn)
    distances = np.array(distances)  # Chuyển về NumPy array
    cosine_similarities = 1 - (distances ** 2) / 2  # Vectorized computation

    # Xây dựng danh sách kết quả
    results = []
    for i, index in enumerate(indices):
        if index in id_mapping:
            if threshold is None or cosine_similarities[i] >= threshold:
                results.append({
                    "id": id_mapping[index]["id"],
                    "full_name": id_mapping[index]["full_name"],
                    "similarity": cosine_similarities[i]
                })

    return results

def search_annoys(query_embeddings, n_neighbors=1, threshold=None):
    """
    Tìm kiếm trong Annoy index với danh sách query_embeddings.

    Parameters:
        - query_embeddings: List các numpy array chứa các query embeddings.
        - n_neighbors: Số lượng hàng xóm gần nhất cần tìm.
        - threshold: Ngưỡng khoảng cách tối đa (nếu None, không áp dụng).

    Returns:
        - Danh sách kết quả [None, result1, None, result2, ...]
    """
    results_list = []
    for query in query_embeddings:
        result = search_annoy(query, n_neighbors, threshold)
        results_list.append(result if result else None)

    return results_list

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
        result = detector.get_face_detects(img)
        face_data = result[0]
        num_faces = face_data.shape[0]

        if num_faces == 0:
            print("No face in this image")
            return None
        elif num_faces > 1:
            print(f"Multiple faces detected in this image ({num_faces} faces)")
            return None

        cropped_faces = detector.crop_faces(img, bounding_boxes=face_data, margin=10)
        embedding = detector.get_face_embeddings(cropped_faces)
    
        return embedding[0]
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None