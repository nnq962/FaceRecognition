from media_manager import MediaManager
import cv2

media_manager = MediaManager(source=0, imgsz=(320, 320))

for path, _, im0s, vid_cap, s in media_manager.dataset:
    for im0 in im0s:
        cv2.imshow("TEST MEDIA MANAGER", im0)
        cv2.waitKey(1) 