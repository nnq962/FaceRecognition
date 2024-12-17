from insightface_detector import InsightFaceDetector
from media_manager import MediaManager

media_manager = MediaManager(source='device.txt', nosave=False, face_recognition=False, face_emotion=False, check_small_face=False)
detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()