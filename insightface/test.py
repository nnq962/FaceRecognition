import argparse

def parse_arguments(rtsp_urls):
    parser = argparse.ArgumentParser(description="Script to handle sources")
    parser.add_argument("--source", required=True, help="Specify the source (e.g., 0, 1, rtsp_camera_1, or all_rtsp_camera)")

    args = parser.parse_args()

    # Xử lý giá trị của `--source`
    source = args.source
    if source.isdigit():  # Nếu là số
        return int(source)  # Trả về số
    elif source.startswith("rtsp_camera_"):  # Nếu là tên camera
        try:
            index = int(source.split("_")[-1]) - 1  # Lấy số từ tên camera, trừ 1 để có index
            return rtsp_urls[index]  # Trả về URL tương ứng
        except (ValueError, IndexError):
            raise ValueError(f"Invalid camera name: {source}")
    elif source == "all_rtsp_camera":  # Nếu là `all_rtsp_camera`
        return rtsp_urls  # Trả về toàn bộ danh sách URLs
    else:
        raise ValueError(f"Invalid source: {source}")

# Ví dụ danh sách RTSP URLs
rtsp_urls = [
    "rtsp://admin:L2620AE7@192.168.1.123:554/cam/realmonitor?channel=1&subtype=0",
    "rtsp://admin:L2A3A7AC@192.168.1.125:554/cam/realmonitor?channel=1&subtype=0",
]

# Chạy hàm parse_arguments
try:
    selected_source = parse_arguments(rtsp_urls)
    print(f"Selected source: {selected_source}")
except ValueError as e:
    print(f"Error: {e}")