import oop1
import oop



media = oop1.MediaManager(source='assets/24person.jpg')
detector = oop.Yolov9Detector(mediamanager=media)
detector.run_inference()


