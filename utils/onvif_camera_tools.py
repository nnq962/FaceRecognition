import re
import ipaddress
from onvif import ONVIFCamera
import socket
from utils.logger_config import LOGGER

class CameraConnectionError(Exception):
    """Exception raised when camera connection fails"""
    pass

class CameraNotFoundError(Exception):
    """Exception raised when camera is not found"""
    pass

class InvalidParameterError(Exception):
    """Exception raised when parameters are invalid"""
    pass

def get_camera_rtsp_url(ip=None, username=None, password=None, mac_address=None, port=80):
    """
    Lấy địa chỉ RTSP của camera ONVIF
    
    Args:
        ip (str, optional): Địa chỉ IP của camera
        username (str): Tên đăng nhập (bắt buộc)
        password (str): Mật khẩu (bắt buộc)
        mac_address (str, optional): Địa chỉ MAC của camera (dùng khi không có IP)
        port (int): Port kết nối (mặc định 80)
    
    Returns:
        str: URL RTSP của main stream
        
    Raises:
        InvalidParameterError: Khi thiếu username/password hoặc format không hợp lệ
        CameraNotFoundError: Khi không tìm thấy camera
        CameraConnectionError: Khi không thể kết nối hoặc lấy RTSP URL
    """
    
    # Validate required parameters
    if not username or not password:
        raise InvalidParameterError("Username và password là bắt buộc")
    
    # Validate port
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise InvalidParameterError("Port phải là số nguyên từ 1 đến 65535")
    
    # Determine IP address
    if ip is None:
        if not mac_address:
            raise InvalidParameterError("Phải cung cấp ip hoặc mac_address")
        
        # Validate MAC address format
        if not _validate_mac_address(mac_address):
            raise InvalidParameterError("Format MAC address không hợp lệ")
        
        # Find IP by MAC address
        ip = _find_ip_by_mac(mac_address, username, password)
        if not ip:
            raise CameraNotFoundError(f"Không tìm thấy camera với MAC address: {mac_address}")
    else:
        # Validate IP address format
        if not _validate_ip_address(ip):
            raise InvalidParameterError("Format IP address không hợp lệ")
    
    # Get RTSP URL
    rtsp_url = _get_rtsp_url_from_camera(ip, username, password, port)
    if not rtsp_url:
        raise CameraConnectionError(f"Không thể lấy RTSP URL từ camera tại {ip}:{port}")
    
    return rtsp_url

def _validate_ip_address(ip):
    """Validate IP address format"""
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False

def _validate_mac_address(mac):
    """Validate MAC address format"""
    # Support formats: xx:xx:xx:xx:xx:xx, xx-xx-xx-xx-xx-xx, xxxxxxxxxxxx
    mac_patterns = [
        r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',  # xx:xx:xx:xx:xx:xx or xx-xx-xx-xx-xx-xx
        r'^[0-9A-Fa-f]{12}$'  # xxxxxxxxxxxx
    ]
    
    for pattern in mac_patterns:
        if re.match(pattern, mac):
            return True
    return False

def _normalize_mac_address(mac):
    """Normalize MAC address to lowercase with colons"""
    # Remove separators and convert to lowercase
    clean_mac = re.sub(r'[:-]', '', mac.lower())
    # Add colons every 2 characters
    return ':'.join(clean_mac[i:i+2] for i in range(0, 12, 2))

def _find_ip_by_mac(mac_address, username, password):
    """Find IP address by MAC address"""
    try:
        # Discover ONVIF devices
        onvif_ips = discover_onvif_devices()
        if not onvif_ips:
            raise CameraNotFoundError("Không tìm thấy camera ONVIF nào trong mạng")
        
        normalized_target_mac = _normalize_mac_address(mac_address)
        
        for ip in onvif_ips:
            try:
                network_configs = get_network_configuration(ip, username, password)
                for config in network_configs:
                    device_mac = _normalize_mac_address(config["MAC Address"])
                    if device_mac == normalized_target_mac:
                        LOGGER.info(f"Tìm thấy camera với MAC {mac_address} tại IP {ip}")
                        return ip
            except Exception as e:
                LOGGER.warning(f"Không thể kết nối đến {ip}: {e}")
                continue
        
        return None
        
    except Exception as e:
        raise CameraConnectionError(f"Lỗi khi tìm kiếm camera: {e}")

def _get_rtsp_url_from_camera(ip, username, password, port):
    """Get RTSP URL from camera"""
    try:
        # Connect to camera
        camera = ONVIFCamera(ip, port, username, password)
        media_service = camera.create_media_service()
        
        # Get video profiles
        profiles = media_service.GetProfiles()
        if not profiles:
            raise CameraConnectionError("Không tìm thấy media profile nào")
        
        # Try to find main stream first (subtype=0)
        main_stream_url = None
        first_profile_url = None
        
        for profile in profiles:
            try:
                # Create stream setup request
                stream_setup = media_service.create_type('GetStreamUri')
                stream_setup.StreamSetup = {
                    'Stream': 'RTP-Unicast',
                    'Transport': {'Protocol': 'RTSP'}
                }
                stream_setup.ProfileToken = profile.token
                
                # Get stream URI
                uri = media_service.GetStreamUri(stream_setup)
                
                # Insert username and password into RTSP URL
                rtsp_url = uri.Uri.replace("rtsp://", f"rtsp://{username}:{password}@")
                
                # Store first profile as fallback
                if first_profile_url is None:
                    first_profile_url = rtsp_url
                
                # Check if this is main stream
                if "subtype=0" in rtsp_url:
                    main_stream_url = rtsp_url
                    break
                    
            except Exception as e:
                LOGGER.warning(f"Không thể lấy stream URI cho profile {profile.Name}: {e}")
                continue
        
        # Return main stream if found, otherwise first profile
        result_url = main_stream_url or first_profile_url
        
        if result_url:
            # LOGGER.info(f"Đã lấy RTSP URL từ camera {ip}: {result_url}")
            return result_url
        else:
            raise CameraConnectionError("Không thể lấy RTSP URL từ bất kỳ profile nào")
            
    except Exception as e:
        raise CameraConnectionError(f"Lỗi khi kết nối camera tại {ip}:{port} - {e}")

# Existing functions from your code (unchanged)
def discover_onvif_devices():
    """Discover ONVIF devices on network"""
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
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5)
    sock.sendto(message, ('239.255.255.250', onvif_port))
    
    discovered_ips = set()
    try:
        while True:
            data, addr = sock.recvfrom(4096)
            discovered_ips.add(addr[0])
    except socket.timeout:
        pass
    
    return list(discovered_ips)

def prefix_to_netmask(prefix_length):
    """Convert prefix length to subnet mask"""
    return str(ipaddress.IPv4Network((0, prefix_length)).netmask)

def get_network_configuration(ip, username, password, port=80):
    """Get network configuration from camera"""
    network_info = []
    try:
        camera = ONVIFCamera(ip, port, username, password)
        network_service = camera.create_devicemgmt_service()
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
        LOGGER.error(f"Failed to get network configuration for {ip}: {e}")
        raise
        
    return network_info