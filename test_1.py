import numpy as np
import time
from annoy import AnnoyIndex

# Số lượng vector và số chiều
num_vectors = 100000
dim = 512

# Tạo dataset ngẫu nhiên và chuẩn hóa
vectors = np.random.rand(num_vectors, dim).astype(np.float32)
vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)  # Chuẩn hóa

# Chọn một vector truy vấn
query_vec = np.random.rand(dim).astype(np.float32)
query_vec /= np.linalg.norm(query_vec)  # Chuẩn hóa

# Khởi tạo Annoy với Euclidean
annoy_euclidean = AnnoyIndex(dim, 'euclidean')
for i, vec in enumerate(vectors):
    annoy_euclidean.add_item(i, vec)
annoy_euclidean.build(10)

# Khởi tạo Annoy với Angular
annoy_angular = AnnoyIndex(dim, 'angular')
for i, vec in enumerate(vectors):
    annoy_angular.add_item(i, vec)
annoy_angular.build(10)

# Tìm kiếm với Euclidean
start_time = time.time()
euclidean_results = annoy_euclidean.get_nns_by_vector(query_vec, 10, include_distances=True)
euclidean_time = time.time() - start_time

# Tìm kiếm với Angular
start_time = time.time()
angular_results = annoy_angular.get_nns_by_vector(query_vec, 10, include_distances=True)
angular_time = time.time() - start_time

# In kết quả
print(f"Annoy Euclidean Search Time: {euclidean_time:.6f} seconds")
print(f"Annoy Angular Search Time: {angular_time:.6f} seconds")