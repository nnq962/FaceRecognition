import camera
import extract_embeddings
from emotion_recognizer import EmotionRecognizer
import cv2
import verify_frame
import time
import subprocess as sp

embedding_folder = 'embeddings_data'
rtsp_url = "rtsp://quyetnguyen:061223@192.168.1.88:554/stream1"

cam_manager = camera.CameraManager(camera_id=0, detector="mediapipe")
verifier = verify_frame.VerifyFrame(data_folder=embedding_folder, threshold=0.4)
get_embs = extract_embeddings.FaceEmbeddingExtractor()
get_emotion = EmotionRecognizer()

# Initialize the last execution time and program start time
last_exec_time = time.time()
program_start_time = time.time()  # Thêm biến để theo dõi thời điểm bắt đầu chương trình

emotions = []
boxes = []
TIME_INTERVAL = 1
TIME_START = 3

# Add RTSP output configuration
RTSP_OUTPUT_URL = "rtsp://localhost:8554/nnqstream"  # Adjust the URL according to your MediaMTX server
FRAME_WIDTH = cam_manager.frame_width  # Adjust as needed
FRAME_HEIGHT = cam_manager.frame_height  # Adjust as needed
FPS = 60

# Initialize FFMPEG process for RTSP streaming
command = [
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', f'{FRAME_WIDTH}x{FRAME_HEIGHT}',
    '-r', str(FPS),
    '-i', '-',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-preset', 'ultrafast',
    '-f', 'rtsp',
    RTSP_OUTPUT_URL
]

rtsp_process = sp.Popen(command, stdin=sp.PIPE)

while True:
    frame = cam_manager.get_frame(flip_code=1)
    
    current_time = time.time()
    
    if (current_time - program_start_time >= TIME_START) and (current_time - last_exec_time >= TIME_INTERVAL):
        boxes = cam_manager.detect_faces(frame)
        embeddings = get_embs.extract_embeddings(frame, boxes)
        result = verifier.verify(embeddings)
        emotions = get_emotion.get_emotion(frame, boxes)
        last_exec_time = current_time
    
    names = result if 'result' in locals() and result else ["Unknown"] * len(boxes)
    frame_with_faces = cam_manager.draw_faces(frame, boxes, names, emotions)
    
    # Write frame to RTSP stream
    rtsp_process.stdin.write(frame_with_faces.tobytes())
    
    cv2.imshow('Camera with Face Detection', frame_with_faces)  
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
rtsp_process.stdin.close()
rtsp_process.wait()
cam_manager.release()
cv2.destroyAllWindows()
