import argparse
from notification_server import send_notification

if __name__ == "__main__":
# Cho test_notification.py
    parser = argparse.ArgumentParser(description="Gửi thông báo tới server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Địa chỉ IP hoặc hostname của server")
    parser.add_argument("--port", type=int, default=14679, help="Cổng control port của server")
    parser.add_argument("--message", type=str, required=True, help="Nội dung thông báo")
    parser.add_argument("--secret-key", type=str, default="3hinc14679", help="Khóa xác thực để gửi thông báo")

    args = parser.parse_args()

    success = send_notification(
        message=args.message, 
        host=args.host, 
        control_port=args.port, 
        secret_key=args.secret_key
    )
    
    if success:
        print("Đã gửi thông báo thành công.")
    else:
        print("Gửi thông báo thất bại.")