from media_manager import MediaManager
from insightface_detector import InsightFaceDetector
import cv2

media = MediaManager()
detector = InsightFaceDetector(media_manager=media)

img = cv2.imread("photo_test/happyandsad.jpg")

data = detector.get_face_detect(img)

for i, item in enumerate(data):
    bbox, confidence, points = item
    print(f"Element {i}:")
    print(f"  Bounding Box: {bbox}")
    print(f"  Confidence: {confidence}")
    print(f"  Points: {points}")
    print("=============")
    
