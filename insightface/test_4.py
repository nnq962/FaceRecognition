from test_5 import InsightFaceDetector
from media_manager import MediaManager

media_manager = MediaManager(source='0', nosave=True, face_recognition=False, face_emotion=False, check_small_face=False, streaming=False, export_data=False)
detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()