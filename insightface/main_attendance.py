from update_basicsr import update_import

# Update basicsr model
update_import(file_path="/usr/local/lib/python3.10/dist-packages/basicsr/data/degradations.py")
update_import(file_path="/home/pc/.conda/envs/nnq_env/lib/python3.10/site-packages/basicsr/data/degradations.py")

import argparse
from insightface_detector import InsightFaceDetector
from media_manager import MediaManager
from get_ip_address_camera import create_rtsp_urls_from_mongo

def process_source(source_arg):
    if source_arg.isdigit():
        camera_ids = [int(source_arg)]
        rtsp_urls = create_rtsp_urls_from_mongo(camera_ids)
        if rtsp_urls:
            return rtsp_urls[0]

    if "," in source_arg:
        device_ids = source_arg.split(",")
        devices = []
        for device_id in device_ids:
            if device_id.isdigit():
                devices.append(device_id)
            else:
                try:
                    camera_ids = [int(id.strip()) for id in device_id.split(",") if id.strip().isdigit()]
                    rtsp_urls = create_rtsp_urls_from_mongo(camera_ids)
                    devices.extend(rtsp_urls)
                except Exception as e:
                    print(f"Error retrieving RTSP URLs: {e}")
                    return None
        with open("device.txt", "w") as f:
            for device in devices:
                f.write(f"{device}\n")
        return "device.txt"

    return source_arg

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
)

detector = InsightFaceDetector(media_manager=media_manager)
detector.run_inference()