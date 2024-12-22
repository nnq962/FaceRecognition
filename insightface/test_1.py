import cv2
from insightface_utils import crop_and_align_faces, search_ids
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager

media_manager = MediaManager(source='datatest/nnq1.jpg', nosave=True, face_recognition=True, face_emotion=False, check_small_face=False, streaming=False, export_data=True)
detector = InsightFaceDetector(media_manager=media_manager)

face_recognition = True

# Danh sách ảnh
img1 = cv2.imread("datatest/happyandsad.jpg")
img2 = cv2.imread("datatest/nnq_test.png")
img3 = cv2.imread("datatest/putin_test.jpg")
imgs = [img1, img2]
img_test = cv2.imread("datatest/thiennhien.jpg")

imgss = [img1]

print(len(img1))

# Phát hiện khuôn mặt
pred = detector.get_face_detects(imgss)

all_cropped_faces = []
metadata = []  # Metadata lưu trữ thông tin cho từng khuôn mặt
face_counts = []  # Số lượng khuôn mặt trong từng ảnh

for i, det in enumerate(pred):  # per image
    if det is None:
        face_counts.append(0)  # Ghi nhận 0 khuôn mặt cho ảnh này
        continue
    
    bboxes, keypoints = det
    if face_recognition:
        cropped_faces = crop_and_align_faces(imgss[i], bboxes, keypoints, 0.5)
        all_cropped_faces.extend(cropped_faces)
    face_counts.append(len(bboxes))

    # Lưu metadata cho mỗi khuôn mặt trong ảnh
    for bbox, kps in zip(bboxes, keypoints):
        metadata.append({
            "image_index": i,
            "bbox": bbox,
            "keypoints": kps
        })

if face_recognition:
        all_embeddings = detector.get_face_embeddings(all_cropped_faces)
        kq = search_ids(all_embeddings, top_k=1, threshold=0.5)

results_per_image = []  # Danh sách chứa kết quả theo từng ảnh
start_idx = 0

for i, count in enumerate(face_counts):  # Duyệt qua từng ảnh
    results = []  # Kết quả cho từng ảnh
    metadata_for_image = metadata[start_idx:start_idx + count]
    ids_for_image = kq[start_idx:start_idx + count] if face_recognition else []

    for meta, id_info in zip(metadata_for_image, ids_for_image):
        result = {
            "bbox": meta["bbox"],
            "keypoints": meta["keypoints"],
            "id": id_info[0]["id"] if id_info else "unknown",
            "similarity": id_info[0]["similarity"] if id_info else None
        }
        results.append(result)

    results_per_image.append(results)
    start_idx += count

# In kết quả của results_per_image
for img_index, faces in enumerate(results_per_image):
    print(f"Image {img_index + 1}: {len(faces)} faces detected")
    for face_index, face in enumerate(faces):
        # print(f"  Face {face_index + 1}:")
        # print(f"    Bounding Box: {face['bbox']}")
        # print(f"    Keypoints: {face['keypoints']}")
        if face_recognition:
            print(f"    ID: {face['id']}")
            print(f"    Similarity: {face['similarity']:.2f}" if face['similarity'] is not None else "    Similarity: N/A")
        else:
            print("    Face recognition disabled, no embedding or ID available.")
    print("=" * 50)    

# Kết quả `results_per_image` có cấu trúc:
# [
#     [  # Ảnh 1
#         {
#             "bbox": <bbox của khuôn mặt 1>,
#             "keypoints": <keypoints của khuôn mặt 1>,
#             "embedding": <embedding của khuôn mặt 1> hoặc None nếu không nhận diện,
#             "id": "Tên ID" hoặc "unknown",
#             "similarity": <độ tương đồng> hoặc None
#         },
#         ...
#     ],
#     [  # Ảnh 2
#         ...
#     ]
# ]




# # Cắt và chuẩn hóa khuôn mặt từ mỗi ảnh
# all_cropped_faces = []
# metadata = []  # Metadata lưu trữ thông tin cho từng khuôn mặt
# face_counts = []  # Số lượng khuôn mặt trong từng ảnh

# for i, det in enumerate(results):  # per image
#     bboxes, keypoints = det
#     cropped_faces = crop_and_align_faces(imgs[i], bboxes, keypoints, 0.5)
#     all_cropped_faces.extend(cropped_faces)
#     face_counts.append(len(cropped_faces))

#     # Lưu metadata cho mỗi khuôn mặt trong ảnh
#     for bbox, kps in zip(bboxes, keypoints):
#         metadata.append({
#             "image_index": i,
#             "bbox": bbox,
#             "keypoints": kps
#         })


# all_normalized_embeddings = detector.get_face_embeddings(all_cropped_faces)

# # Phân phối lại embedding và metadata theo ảnh
# start_idx = 0
# results_per_image = []  # Danh sách chứa kết quả theo từng ảnh

# for img_idx, count in enumerate(face_counts):
#     results = []
#     embeddings_for_image = all_normalized_embeddings[start_idx:start_idx + count]
#     metadata_for_image = metadata[start_idx:start_idx + count]

#     for emb, meta in zip(embeddings_for_image, metadata_for_image):
#         results.append({
#             "bbox": meta["bbox"],
#             "keypoints": meta["keypoints"],
#             "embedding": emb
#         })

#     results_per_image.append(results)
#     start_idx += count

# # Hiển thị kết quả
# for img_idx, results in enumerate(results_per_image):
#     print(f"Image {img_idx + 1}: {len(results)} faces detected.")
#     for face_idx, face_data in enumerate(results):
#         print(f"  Face {face_idx + 1}:")
#         # print(f"    BBox: {face_data['bbox']}")
#         # print(f"    Keypoints: {face_data['keypoints']}")
#         print(f"    Embedding (first 5 values): {face_data['embedding'][:5]}")
#     print("================================================================")