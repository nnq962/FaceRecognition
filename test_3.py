from onvif import ONVIFCamera
import socket
import ipaddress


# ----------------------------------------------------------------
def discover_onvif_devices():
    # Cổng mặc định của ONVIF là 3702
    onvif_port = 3702
    message = """
        <e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
                    xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
                    xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
                    xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
            <e:Header>
                <w:MessageID>uuid:12345678-1234-1234-1234-123456789abc</w:MessageID>
                <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
                <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
            </e:Header>
            <e:Body>
                <d:Probe>
                    <d:Types>dn:NetworkVideoTransmitter</d:Types>
                </d:Probe>
            </e:Body>
        </e:Envelope>
    """.strip().encode("utf-8")

    # Gửi broadcast qua UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5)

    # Gửi đến broadcast address
    sock.sendto(message, ('239.255.255.250', onvif_port))

    discovered_ips = set()  # Sử dụng set để tránh trùng lặp IP

    try:
        while True:
            data, addr = sock.recvfrom(4096)
            discovered_ips.add(addr[0])
    except socket.timeout:
        pass  # Kết thúc khi hết thời gian chờ

    return list(discovered_ips)


# ----------------------------------------------------------------
def get_rtsp_url(ip, username, password, port=80):
    rtsp_urls = {}

    try:
        # Kết nối với camera
        camera = ONVIFCamera(ip, port, username, password)
        media_service = camera.create_media_service()
        
        # Lấy profile video
        profiles = media_service.GetProfiles()
        
        if not profiles:
            print(f"No media profiles found for camera at {ip}.")
            return rtsp_urls
        
        for profile in profiles:
            # Tạo request lấy RTSP URL
            stream_setup = media_service.create_type('GetStreamUri')
            stream_setup.StreamSetup = {
                'Stream': 'RTP-Unicast',
                'Transport': {'Protocol': 'RTSP'}
            }
            stream_setup.ProfileToken = profile.token
            
            # Gửi request
            uri = media_service.GetStreamUri(stream_setup)
            rtsp_urls[profile.Name] = uri.Uri

    except Exception as e:
        print(f"Failed to get RTSP URL from {ip} (Port: {port}): {e}")

    return rtsp_urls


# ----------------------------------------------------------------
def prefix_to_netmask(prefix_length):
    """Chuyển prefix length thành subnet mask (ví dụ: 24 -> 255.255.255.0)"""
    return str(ipaddress.IPv4Network((0, prefix_length)).netmask)


# ----------------------------------------------------------------
def get_network_configuration(ip, username, password, port=80):
    network_info = []

    try:
        camera = ONVIFCamera(ip, port, username, password)
        network_service = camera.create_devicemgmt_service()

        # Lấy cấu hình mạng
        network_interfaces = network_service.GetNetworkInterfaces()
        
        for interface in network_interfaces:
            ipv4 = interface.IPv4.Config.Manual[0] if interface.IPv4.Config.Manual else None
            ip_address = ipv4.Address if ipv4 else "DHCP"
            subnet_mask = prefix_to_netmask(ipv4.PrefixLength) if ipv4 else "Unknown"

            interface_info = {
                "Interface": interface.Info.Name,
                "MAC Address": interface.Info.HwAddress,
                "IP Address": ip_address,
                "Subnet Mask": subnet_mask,
                "DHCP Enabled": interface.IPv4.Config.DHCP
            }

            network_info.append(interface_info)

    except Exception as e:
        print(f"Failed to get network configuration for {ip}: {e}")

    return network_info


# ----------------------------------------------------------------
def find_main_stream_rtsp(mac_address, username, password):
    # Bước 1: Tìm tất cả các IP camera ONVIF
    onvif_ips = discover_onvif_devices()

    for ip in onvif_ips:
        # Bước 2: Lấy thông tin cấu hình mạng để so sánh MAC Address
        try:
            network_configs = get_network_configuration(ip, username, password)
        except Exception as e:
            print(f"Authorization failed for IP {ip}: {e}")
            continue  # Bỏ qua IP nếu lỗi xác thực

        for config in network_configs:
            if config["MAC Address"].lower() == mac_address.lower():
                # Bước 3: Lấy RTSP URL và chọn luồng chính (subtype=0)
                rtsp_urls = get_rtsp_url(ip, username, password)
                for profile_name, url in rtsp_urls.items():
                    if "subtype=0" in url:
                        return url
                print(f"Main stream not found for IP {ip}")
    print(f"Device with MAC {mac_address} not found.")
    return None

mac = "a8:31:62:a3:30:cf"
username = "admin"
password = "L2620AE7"

main_stream_url = find_main_stream_rtsp(mac, username, password)
print("Main Stream RTSP URL:", main_stream_url)