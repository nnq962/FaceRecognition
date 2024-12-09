import camera
import extract_embeddings
from emotion_recognizer import EmotionRecognizer
import cv2
import verify_frame
import time  # Import the time module

embedding_folder = 'embeddings_data'
rtsp_url = "rtsp://quyetnguyen:061223@192.168.1.88:554/stream1"

cam_manager = camera.CameraManager(camera_id=2, detector="mtcnn")
verifier = verify_frame.VerifyFrame(data_folder=embedding_folder, threshold=0.4)
get_embs = extract_embeddings.FaceEmbeddingExtractor()
get_emotion = EmotionRecognizer()

# Initialize the last execution time and program start time
last_exec_time = time.time()
program_start_time = time.time()  # Thêm biến để theo dõi thời điểm bắt đầu chương trình

emotions = []
boxes = []
TIME_INTERVAL = 0.5
TIME_START = 3

while True:
    frame = cam_manager.get_frame(flip_code=1)
    
    current_time = time.time()
    
    # Kiểm tra nếu đã qua 5 giây kể từ khi bắt đầu và đã đến thời điểm cập nhật
    if (current_time - program_start_time >= TIME_START) and (current_time - last_exec_time >= TIME_INTERVAL):
        boxes = cam_manager.detect_faces(frame)
        embeddings = get_embs.extract_embeddings(frame, boxes)
        result = verifier.verify(embeddings)
        emotions = get_emotion.get_emotion(frame, boxes)
        last_exec_time = current_time
    
    # Use the latest result if available
    names = result if 'result' in locals() and result else ["Unknown"] * len(boxes)

    frame_with_faces = cam_manager.draw_faces(frame, boxes, names, emotions)
    cv2.imshow('Camera with Face Detection', frame_with_faces)  
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam_manager.release()
cv2.destroyAllWindows()
