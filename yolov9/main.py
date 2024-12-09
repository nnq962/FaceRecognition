import media_manager
import yolov9_detector

media = media_manager.MediaManager(source="0", save_crop=False, nosave=False)
detector = yolov9_detector.Yolov9Detector(mediamanager=media, device='mps', emotion=True, line_thickness=3)
detector.run_inference()


