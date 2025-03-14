from scapy.all import ARP, Ether, srp

def find_ip_by_mac_scapy(target_mac, subnet="192.168.1.0/24", timeout=2):
    """
    Quét mạng trong dải địa chỉ subnet bằng cách gửi gói ARP để tìm IP ứng với địa chỉ MAC.
    
    Parameters:
        target_mac (str): Địa chỉ MAC cần tìm.
        subnet (str): Dải địa chỉ quét (mặc định: "192.168.1.0/24").
        timeout (int): Thời gian chờ phản hồi (giây).
        
    Returns:
        str or None: Địa chỉ IP nếu tìm thấy, ngược lại None.
        
    Lưu ý: Phương pháp này thường yêu cầu quyền root để gửi/nhận gói tin.
    """
    # Tạo gói tin ARP request gói chung (broadcast)
    arp_request = ARP(pdst=subnet)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = broadcast / arp_request

    # Gửi gói tin và nhận các phản hồi
    result = srp(packet, timeout=timeout, verbose=0)[0]
    
    # Duyệt qua các phản hồi và kiểm tra địa chỉ MAC
    for sent, received in result:
        if received.hwsrc.lower() == target_mac.lower():
            return received.psrc  # Trả về địa chỉ IP của host
    return None

# Ví dụ sử dụng:
if __name__ == "__main__":
    target_mac = "a8:31:62:a3:30:c7"  # Thay đổi địa chỉ MAC cần tìm
    ip = find_ip_by_mac_scapy(target_mac, subnet="192.168.1.0/24")
    if ip:
        print(f"Địa chỉ IP của {target_mac} là: {ip}")
    else:
        print("Không tìm thấy địa chỉ IP cho địa chỉ MAC đã cho.")