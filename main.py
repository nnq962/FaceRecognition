from config import config
import argparse
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from websocket_server import start_ws_server


parser = argparse.ArgumentParser(description="Run face detection and analysis.")
parser.add_argument("--source", type=str, required=True, help="Source for the media (e.g., '0' for webcam or a video file path).")
parser.add_argument("--save", action="store_true", help="Enable saving processed media.")
parser.add_argument("--face_recognition", action="store_true", help="Enable face recognition.")
parser.add_argument("--face_emotion", action="store_true", help="Enable face emotion analysis.")
parser.add_argument("--export_data", action="store_true", help="Enable data export.")
parser.add_argument("--time_to_save", type=int, default=5, help="Time interval (in seconds) to save exported data.")
parser.add_argument("--raise_hand", action="store_true", help="Enable raise hand detection.")
parser.add_argument("--view_img", action="store_true", help="Enable display.")
parser.add_argument("--line_thickness", type=int, default=3, help="Line thickness")
parser.add_argument("--qr_code", action="store_true", help="Enable qr code.")
parser.add_argument("--face_mask", action="store_true", help="Enable face mask detection.")
parser.add_argument("--notification", action="store_true", help="Turn on voice notifications.")


args = parser.parse_args()
processed_source = config.process_camera_input(args.source)

if args.raise_hand or args.qr_code:
    start_ws_server()

media_manager = MediaManager(
    source=processed_source,
    save=args.save,
    view_img=args.view_img,
    line_thickness=args.line_thickness
)

detector = InsightFaceDetector(
    media_manager=media_manager,
    face_recognition=args.face_recognition,
    face_emotion=args.face_emotion,
    face_mask=args.face_mask,
    raise_hand=args.raise_hand,
    qr_code=args.qr_code,
    export_data=args.export_data,
    time_to_save=args.time_to_save,
    notification=args.notification
)

detector.run_inference()