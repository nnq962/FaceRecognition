import cv2
from insightface_utils import crop_and_align_faces, search_ids
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager

media_manager = MediaManager(source='datatest/nnq1.jpg', nosave=True, face_recognition=True, face_emotion=False, check_small_face=False, streaming=False, export_data=True)
detector = InsightFaceDetector(media_manager=media_manager)


img = cv2.imread("datatest/happyandsad.jpg")

imgss = [img]

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

all_embeddings = detector.get_face_embeddings(all_cropped_faces)
kq = search_ids(all_embeddings, top_k=1, threshold=0.5)
print("DONE")