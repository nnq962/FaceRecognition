import faiss
import numpy as np
import time

# Load FAISS index
index = faiss.read_index("face_index.faiss")

# Load ID mapping từ .npy
start_load = time.time()
user_ids = np.load("id_mapping.npy")
end_load = time.time()
print(f"Thời gian load ID mapping từ .npy: {end_load - start_load:.6f} giây")

# Tạo vector truy vấn
d = index.d
query_vector = np.random.rand(1, d).astype('float32')
query_vector /= np.linalg.norm(query_vector)

# Đo thời gian tìm kiếm
start_search = time.time()
D, I = index.search(query_vector, k=1)
end_search = time.time()
matched_id = user_ids[I[0][0]]

print(f"Người được xác minh: {matched_id}, độ tương đồng: {D[0][0]}")
print(f"Thời gian tìm kiếm: {end_search - start_search:.6f} giây")