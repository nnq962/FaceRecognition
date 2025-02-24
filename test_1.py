from insightface_detector import InsightFaceDetector
from insightface_utils import process_image, search_annoy
from config import config

detector = InsightFaceDetector()

img = "data_test/nnq1.jpg"
query_embedding = process_image(img, detector=detector)

# Chỉ lấy 1 hàng xóm gần nhất cho mỗi query
results = search_annoy(query_embedding, n_neighbors=3, threshold=None)

print(results)
