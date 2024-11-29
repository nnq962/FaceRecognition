from retinaface import RetinaFace

import time

start = time.time()
resp = RetinaFace.detect_faces("photo_test/24person.jpg")
print("time: ", time.time() - start)
# print(resp)