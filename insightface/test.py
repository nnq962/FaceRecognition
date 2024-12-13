from media_manager import MediaManager
from insightface_detector import InsightFaceDetector
import cv2

media = MediaManager(source='0')
detector = InsightFaceDetector(media_manager=media)
detector.run_inference()