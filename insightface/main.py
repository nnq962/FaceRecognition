from insightface_detector import InsightFaceDetector
from media_manager import MediaManager

media_manager = MediaManager(source='0', nosave=True, face_recognition=True, face_emotion=True)
detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()