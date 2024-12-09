import faiss
import numpy as np

class FaissANN:
    def __init__(self, dimension=128, use_gpu=False):
        """
        Khởi tạo FAISS ANN với phương pháp tìm kiếm L2 (IndexFlatL2).
        :param dimension: Số chiều của vector embedding
        :param use_gpu: Có sử dụng GPU hay không
        """
        self.dimension = dimension
        self.use_gpu = use_gpu

        # Sử dụng IndexFlatL2 (không cần huấn luyện)
        self.index = faiss.IndexFlatL2(dimension)

        # Danh sách lưu trữ tất cả embeddings đã thêm
        self.embeddings_list = []

        # Nếu cần sử dụng GPU
        if use_gpu:
            res = faiss.StandardGpuResources()
            self.index = faiss.index_cpu_to_gpu(res, 0, self.index)

    def add_embeddings(self, embeddings):
        """
        Thêm các embedding vào chỉ mục FAISS.
        :param embeddings: Một mảng numpy chứa các embedding (có kích thước [N, dimension])
        """
        assert embeddings.shape[1] == self.dimension, "Dimension mismatch!"
        self.index.add(embeddings)
        self.embeddings_list.append(embeddings)

    def search(self, query_embedding, k=5):
        """
        Tìm kiếm các vector gần nhất với vector truy vấn.
        :param query_embedding: Vector truy vấn có kích thước [1, dimension]
        :param k: Số lượng hàng xóm gần nhất cần tìm
        :return: Các chỉ số của k vector gần nhất và khoảng cách tương ứng
        """
        assert query_embedding.shape[1] == self.dimension, "Dimension mismatch!"
        distances, indices = self.index.search(query_embedding, k)
        return indices, distances

    def get_nearest_embeddings(self, query_embedding, k=5):
        """
        Trả về danh sách các embedding gần nhất dựa trên chỉ số tìm kiếm.
        :param query_embedding: Vector truy vấn có kích thước [1, dimension]
        :param k: Số lượng hàng xóm gần nhất cần tìm
        :return: Danh sách các embedding gần nhất
        """
        indices, _ = self.search(query_embedding, k)
        nearest_embeddings = []

        # Lấy các embedding gần nhất dựa vào chỉ số
        for idx in indices[0]:
            nearest_embeddings.append(self.embeddings_list[0][idx])

        return nearest_embeddings   
