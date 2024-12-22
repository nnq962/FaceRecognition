from insightface_detector import InsightFaceDetector
from media_manager import MediaManager

media_manager = MediaManager(source='0', 
                             nosave=True, 
                             face_recognition=True, 
                             face_emotion=True, 
                             check_small_face=False, 
                             streaming=False, 
                             export_data=False, 
                             time_to_save=8,
                             show_time_process=True)

detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()