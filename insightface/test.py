from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
import cv2

media_manager = MediaManager(source='datatest/happyandsad.jpg', nosave=True, face_recognition=True, face_emotion=True, check_small_face=False, streaming=False, export_data=True)
detector = InsightFaceDetector(media_manager=media_manager)

img = cv2.imread("datatest/happyandsad.jpg")
result = detector.get_face_detect(img)

for bbox, kps, conf in result[0]:
    emb = detector.get_face_embedding(img, bbox, kps, conf)
    print(emb[:5])