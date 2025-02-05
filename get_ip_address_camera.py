import subprocess
from config import config

def get_ip_from_mac(mac_addresses):
    try:
        # Chạy lệnh `arp -a` để lấy danh sách các thiết bị trong mạng
        result = subprocess.check_output(['arp', '-a'], text=True)
        
        # Tạo dictionary để lưu kết quả
        mac_to_ip = {mac.lower(): None for mac in mac_addresses}
        
        # Duyệt qua các dòng trong kết quả để tìm địa chỉ MAC
        for line in result.splitlines():
            for mac in mac_to_ip.keys():
                if mac in line.lower():
                    # Tách địa chỉ IP từ dòng chứa MAC
                    parts = line.split()
                    ip_address = [part for part in parts if "(" in part and ")" in part]
                    if ip_address:
                        mac_to_ip[mac] = ip_address[0].strip("()")  # Lấy địa chỉ IP
        return mac_to_ip
    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_rtsp_urls(mac_to_ip, credentials):
    rtsp_urls = []
    for mac, ip in mac_to_ip.items():
        if ip:
            # Lấy thông tin tài khoản từ credentials
            username, password = credentials.get(mac, ("", ""))
            rtsp_url = f"rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0"
            rtsp_urls.append(rtsp_url)
    return rtsp_urls

def create_rtsp_urls_from_mongo(camera_ids):
    """
    Tạo danh sách RTSP URLs dựa trên danh sách _id của camera trong MongoDB.

    Args:
        camera_ids (list): Danh sách _id của các camera cần lấy RTSP URLs.

    Returns:
        list: Danh sách các URL RTSP tương ứng với các _id.
    """
    camera_collection = config.camera_collection

    # Truy vấn dữ liệu từ MongoDB với _id được cung cấp
    cameras = camera_collection.find({"_id": {"$in": camera_ids}}, {"MAC_address": 1, "user": 1, "password": 1, "_id": 0})
    credentials = {}
    mac_addresses = []

    # Lấy thông tin MAC address, user, và password
    for camera in cameras:
        mac = camera.get("MAC_address", "").lower()
        user = camera.get("user", "")
        password = camera.get("password", "")
        if mac:
            credentials[mac] = (user, password)
            mac_addresses.append(mac)

    # Lấy IP từ MAC address
    mac_to_ip = get_ip_from_mac(mac_addresses)

    # Tạo đường dẫn RTSP
    rtsp_urls = generate_rtsp_urls(mac_to_ip, credentials)

    return rtsp_urls