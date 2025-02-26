from config import config
import argparse
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from websocket_server import start_ws_server

def process_source(source_arg):
    """
    Process the source argument to determine the type of input.
    - '0': Webcam
    - Single camera ID: Generate RTSP URL
    - Multiple camera IDs: Write RTSP URLs or webcam ID to device.txt
    """
    if source_arg.isdigit():  # Single numeric ID (e.g., '0' or '1')
        if source_arg == "0":  # Webcam
            config.camera_names.append("webcam")
            return "0"
        else:  # Single camera
            rtsp_urls = config.create_rtsp_urls_from_mongo([int(source_arg)])
            if rtsp_urls:
                return rtsp_urls[0]
            else:
                raise ValueError(f"Could not retrieve RTSP URL for camera ID: {source_arg}")

    if "," in source_arg:  # Multiple IDs (e.g., '0,1,2')
        device_ids = source_arg.split(",")
        devices = []
        for device_id in device_ids:
            if device_id.strip().isdigit():  # Webcam or camera ID
                if device_id.strip() == "0":  # Webcam
                    devices.append("0")
                else:
                    rtsp_urls = config.create_rtsp_urls_from_mongo([int(device_id.strip())])
                    if rtsp_urls:
                        devices.extend(rtsp_urls)
                    else:
                        raise ValueError(f"Could not retrieve RTSP URL for camera ID: {device_id.strip()}")
        # Write to device.txt
        with open("device.txt", "w") as f:
            for device in devices:
                f.write(f"{device}\n")
        return "device.txt"

    return source_arg  # If it's not numeric or a list, assume it's a file path


parser = argparse.ArgumentParser(description="Run face detection and analysis.")
parser.add_argument("--source", type=str, required=True, help="Source for the media (e.g., '0' for webcam or a video file path).")
parser.add_argument("--save", action="store_true", help="Enable saving processed media.")
parser.add_argument("--face_recognition", action="store_true", help="Enable face recognition.")
parser.add_argument("--face_emotion", action="store_true", help="Enable face emotion analysis.")
parser.add_argument("--check_small_face", action="store_true", help="Enable small face checking.")
parser.add_argument("--streaming", action="store_true", help="Enable streaming mode.")
parser.add_argument("--export_data", action="store_true", help="Enable data export.")
parser.add_argument("--time_to_save", type=int, default=5, help="Time interval (in seconds) to save exported data.")
parser.add_argument("--show_time_process", action="store_true", help="Enable display of process time.")
parser.add_argument("--raise_hand", action="store_true", help="Enable raise hand detection.")
parser.add_argument("--view_img", action="store_true", help="Enable display.")
parser.add_argument("--line_thickness", type=int, default=3, help="Line thickness")
parser.add_argument("--qr_code", action="store_true", help="Enable qr code detection.")

args = parser.parse_args()

processed_source = process_source(args.source)
if processed_source is None:
    print("Failed to process --source. Exiting.")
    exit(1)

if isinstance(processed_source, str) and processed_source == "device.txt":
    print("\nGenerated device.txt with the following sources:")
    with open(processed_source, "r") as f:
        print(f.read())
else:
    print(f"\nProcessing source: {processed_source}\n")

media_manager = MediaManager(
    source=processed_source,
    save=args.save,
    face_recognition=args.face_recognition,
    face_emotion=args.face_emotion,
    check_small_face=args.check_small_face,
    streaming=args.streaming,
    export_data=args.export_data,
    time_to_save=args.time_to_save,
    show_time_process=args.show_time_process,
    raise_hand=args.raise_hand,
    view_img=args.view_img,
    line_thickness=args.line_thickness,
    qr_code=args.qr_code
)

if args.raise_hand or args.qr_code:
    start_ws_server()

detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()