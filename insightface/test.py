from pathlib import Path
from utils.dataloaders import LoadImages, LoadStreams, LoadScreenshots, IMG_FORMATS, VID_FORMATS


def generate_collection_names(source):
    """
    Tạo danh sách tên collection dựa trên đầu vào source.

    Parameters:
        source (str): Đầu vào, có thể là số, đường dẫn RTSP, hoặc tệp chứa danh sách.

    Returns:
        list: Danh sách tên collection.
    """
    # Kiểm tra loại nguồn
    is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
    is_webcam = source.isnumeric() or source.lower().startswith('screen')  # Webcam

    collections = []

    # Nếu là tệp chứa danh sách
    if source.endswith(".txt"):
        with open(source, "r") as file:
            lines = file.readlines()
            for index, line in enumerate(lines):
                line = line.strip()  # Loại bỏ ký tự xuống dòng
                if line.isnumeric():  # Nếu là webcam (số 0, 1, ...)
                    collections.append(f"webcam_{line}")
                elif line.lower().startswith("rtsp://"):  # Nếu là đường dẫn RTSP
                    collections.append(f"rtspcamera_{index}")
    elif is_webcam:  # Nếu là webcam
        collections.append(f"webcam_{source}")
    elif is_url:  # Nếu là URL RTSP
        collections.append(f"rtspcamera_0")

    return collections

