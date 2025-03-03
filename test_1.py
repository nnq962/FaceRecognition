from insightface_detector import InsightFaceDetector
import insightface_utils
import cv2
detector = InsightFaceDetector()

img = 'data_test/nnq1.jpg'

results = insightface_utils.process_image(img, detector)

print(results)