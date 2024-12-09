import face_recognition
import os
import ann
import numpy as np
import pandas as pd


class VerifyFrame:
    def __init__(self, data_folder="embeddings_data", threshold=0.4):
        """
        Khởi tạo lớp VerifyFrame và nạp dữ liệu embeddings và metadata.
        :param data_folder: Thư mục chứa các tệp embeddings và metadata.
        :param threshold: Ngưỡng để xác định sự khớp trong so sánh mặt.
        """
        # Load known embeddings và tên từ metadata
        self.embeddings = np.load(os.path.join(data_folder, 'embeddings.npy'))
        self.metadata = pd.read_csv(os.path.join(data_folder, 'metadata.csv'))

        # Khởi tạo FAISS ANN và thêm embeddings
        dimension = self.embeddings.shape[1]
        self.faiss_ann = ann.FaissANN(dimension)
        self.faiss_ann.add_embeddings(self.embeddings)

        self.name = []
        self.threshold = threshold  # Thêm thuộc tính threshold
    
    def verify(self, unknown_embeddings):
        """
        So sánh các embedding chưa biết với embedding đã biết thông qua ANN và face_recognition.
        :param unknown_embeddings: List các embedding chưa biết.
        :return: List các tên tương ứng nếu khớp, nếu không thì trả về "Unknown".
        """
        self.name = []

        for unknown_embedding in unknown_embeddings:
            name_found = "Unknown"

            # Lấy các embeddings gần nhất từ ANN
            nearest_embeddings = self.get_ann(unknown_embedding)

            # So sánh tất cả các known_embedding cùng một lúc
            known_embeddings = [embedding for embedding, _ in nearest_embeddings]
            known_names = [name for _, name in nearest_embeddings]
            matches = face_recognition.compare_faces(
                known_embeddings, unknown_embedding, tolerance=self.threshold
            )
            # Tìm tên thứ nhất mà có kết quả khớp
            matched_names = [name for match, name in zip(matches, known_names) if match]
            if matched_names:
                name_found = matched_names[0]

            self.name.append(name_found)

        return self.name

    def get_ann(self, unknown_embedding):
        """
        Trả về 2 embeddings gần nhất cùng với tên người của chúng.
        
        :param unknown_embedding: Embedding chưa biết.
        :return: List chứa 2 tuples, mỗi tuple gồm embedding và tên tương ứng.
                Ví dụ: [(embedding1, 'Name1'), (embedding2, 'Name2')]
        """
        query_embedding = np.array(unknown_embedding).reshape(1, -1)
        indices, _ = self.faiss_ann.search(query_embedding, k=2)
        
        nearest_embeddings = []
        for idx in indices[0]:
            embedding = self.embeddings[idx]
            name = self.metadata.iloc[idx]['name']
            nearest_embeddings.append((embedding, name))
        
        return nearest_embeddings
    
    def get_name(self):
        """
        Trả về danh sách các tên sau khi so sánh.
        """
        return self.name
