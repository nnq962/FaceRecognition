import numpy as np
import time
from annoy import AnnoyIndex

# Cấu hình file
ANN_FILE = "face_index.ann"
MAPPING_FILE = "annoy_mapping.npy"
VECTOR_DIM = 512  # Số chiều của embedding

def search_annoy(query_embedding, n_neighbors=5, threshold=None):
    """
    Tìm kiếm trong Annoy index với ngưỡng tùy chỉnh.
    """

    # Load Annoy index
    t = AnnoyIndex(VECTOR_DIM, 'angular')
    t.load(ANN_FILE)

    # Load mapping từ file npy
    id_mapping = np.load(MAPPING_FILE, allow_pickle=True).item()

    # Tìm n_neighbors gần nhất
    nearest_indices = t.get_nns_by_vector(query_embedding, n_neighbors, include_distances=True)

    # nearest_indices[0] = danh sách index
    # nearest_indices[1] = danh sách khoảng cách tương ứng
    indices, distances = nearest_indices

    results = []
    for index, distance in zip(indices, distances):
        if index in id_mapping:
            # Nếu có threshold, chỉ lấy những kết quả có khoảng cách nhỏ hơn threshold
            if threshold is None or distance <= threshold:
                results.append({
                    "user_id": id_mapping[index]["user_id"],
                    "photo_name": id_mapping[index]["photo_name"],
                    "distance": distance
                })

    return results

# Tạo danh sách 100 query_embeddings
num_queries = 1000
query_embeddings = [np.random.randn(VECTOR_DIM).astype(np.float32) for _ in range(num_queries)]

# Đo thời gian chạy
start_time = time.time()

# Chạy vòng lặp tìm kiếm
results_list = []
for query in query_embeddings:
    results_list.append(search_annoy(query, n_neighbors=5, threshold=0.5))

end_time = time.time()
elapsed_time = end_time - start_time

# Hiển thị thời gian chạy
print(f"⏳ Tổng thời gian tìm kiếm 100 query: {elapsed_time:.4f} giây")
print(f"⚡ Trung bình mỗi query mất {elapsed_time/num_queries:.6f} giây")
