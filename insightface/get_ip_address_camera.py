import subprocess

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

mac_credentials = {
    "a8:31:62:a3:30:cf": ("admin", "L2620AE7"),
    "a8:31:62:a3:30:c7": ("admin", "L2A3A7AC"),
}

mac_addresses = list(mac_credentials.keys())
mac_to_ip = get_ip_from_mac(mac_addresses)
rtsp_urls = generate_rtsp_urls(mac_to_ip, mac_credentials)
print(rtsp_urls)