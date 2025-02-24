from yolo_detector import YoloDetector
from yolo_detector_utils import process_image
import cv2

img1 = "data_test/nnq1.jpg"
img2 = "data_test/2person.jpg"

detector = YoloDetector()

result = process_image(img1, detector=detector)

print(result)
