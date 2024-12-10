import media_manager
import yolov9_detector
import sys

os_info = sys.platform
if os_info == 'linux':
    device = ''
elif os_info == 'darwin':
    device = 'mps'
else:
    device = 'cpu'

media = media_manager.MediaManager(source='0', save_crop=False, nosave=False)
detector = yolov9_detector.Yolov9Detector(mediamanager=media, device=device, emotion=True, line_thickness=3)
detector.run_inference()