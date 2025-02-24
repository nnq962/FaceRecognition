from yolo_detector_utils import process_image
from yolo_detector import YoloDetector

detector = YoloDetector()

image_path = "data_test/24person.jpg"

result = process_image(image_path, detector)
print(result)