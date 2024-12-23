import argparse
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from update_basicsr import update_import
from mediamtx_controller import MediaMTXController

# Update basicsr model
update_import()
controller = MediaMTXController()
controller.start()

parser = argparse.ArgumentParser(description="Run face detection and analysis.")

parser.add_argument("--source", type=str, required=True, help="Source for the media (e.g., '0' for webcam or a video file path).")
parser.add_argument("--save", action="store_true", help="Enable saving processed media.")
parser.add_argument("--face_recognition", action="store_true", help="Enable face recognition.")
parser.add_argument("--face_emotion", action="store_true", help="Enable face emotion analysis.")
parser.add_argument("--check_small_face", action="store_true", help="Enable small face checking.")
parser.add_argument("--streaming", action="store_true", help="Enable streaming mode.")
parser.add_argument("--export_data", action="store_true", help="Enable data export.")
parser.add_argument("--time_to_save", type=int, default=8, help="Time interval (in seconds) to save exported data.")
parser.add_argument("--show_time_process", action="store_true", help="Enable display of process time.")

args = parser.parse_args()

media_manager = MediaManager(
    source=args.source,
    save=args.save,
    face_recognition=args.face_recognition,
    face_emotion=args.face_emotion,
    check_small_face=args.check_small_face,
    streaming=args.streaming,
    export_data=args.export_data,
    time_to_save=args.time_to_save,
    show_time_process=args.show_time_process
)

detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()