import argparse
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from get_ip_address_camera import get_ip_from_mac, generate_rtsp_urls
from websocket_server import start_ws_server

mac_credentials = {
    "a8:31:62:a3:30:cf": ("admin", "L2620AE7"),
    "a8:31:62:a3:30:c7": ("admin", "L2A3A7AC"),
}

mac_addresses = list(mac_credentials.keys())
mac_to_ip = get_ip_from_mac(mac_addresses)
rtsp_urls = generate_rtsp_urls(mac_to_ip, mac_credentials)

def process_source_argument(source, rtsp_urls):
    if source.isdigit():
        return int(source)
    elif source.startswith("rtsp_camera_"):
        try:
            index = int(source.split("_")[-1]) - 1
            return rtsp_urls[index]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid camera name: {source}")
    elif source == "all_rtsp_camera":
        file_path = "device.txt"
        with open(file_path, "w") as f:
            for url in rtsp_urls:
                f.write(url + "\n")
        return file_path
    else:
        raise ValueError(f"Invalid source: {source}")

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
parser.add_argument("--raise_hand", action="store_true", help="Enable raise hand dectection.")

args = parser.parse_args()

try:
    processed_source = process_source_argument(args.source, rtsp_urls)
    print(f"\nProcessed source: {processed_source}\n")
except ValueError as e:
    print(f"Error: {e}")
    exit(1)

media_manager = MediaManager(
    source="data_test/nnq1.jpg",
    save=args.save,
    face_recognition=args.face_recognition,
    face_emotion=args.face_emotion,
    check_small_face=args.check_small_face,
    streaming=args.streaming,
    export_data=args.export_data,
    time_to_save=args.time_to_save,
    show_time_process=args.show_time_process,
    raise_hand=args.raise_hand
)

if args.raise_hand:
    start_ws_server()

detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()