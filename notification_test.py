import argparse
import json
import sys
from notification_server import send_notification

if __name__ == "__main__":
    # Đường dẫn đến file cấu hình
    CONFIG_FILE = "main_config.json"

    # Thiết lập parser tham số dòng lệnh
    parser = argparse.ArgumentParser(description="Gửi thông báo tới server")
    parser.add_argument("--config", type=str, help="Configuration profile to use (e.g., 3HINC, EDULIVE)")
    parser.add_argument("--message", type=str, default="Xin chào", help="Nội dung thông báo")
    parser.add_argument("--repeat", type=int, default=1, help="Số lần lặp lại thông báo")
    
    args = parser.parse_args()
    
    # Cấu hình mặc định
    DEFAULT_HOST = "192.168.1.142"
    DEFAULT_PORT = 9625
    DEFAULT_SECRET_KEY = "3hinc"
    
    # Nếu có chỉ định config, đọc từ file JSON
    if args.config:
        try:
            with open(CONFIG_FILE, 'r') as file:
                all_configs = json.load(file)
                
            # Kiểm tra xem config được chỉ định có tồn tại không
            if args.config not in all_configs:
                print(f"Error: Configuration '{args.config}' not found in {CONFIG_FILE}")
                print(f"Available configurations: {', '.join(all_configs.keys())}")
                sys.exit(1)
                
            # Lấy cấu hình từ file
            config = all_configs[args.config]
            host = config.get("host", DEFAULT_HOST)
            port = config.get("noti_control_port", DEFAULT_PORT)
            secret_key = config.get("noti_secret_key", DEFAULT_SECRET_KEY)
            
            print(f"Loaded configuration for '{args.config}'")
            print(f"Host: {host}, Control Port: {port}")
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading config file: {e}")
            print("Using default configuration.")
            host = DEFAULT_HOST
            port = DEFAULT_PORT
            secret_key = DEFAULT_SECRET_KEY
    else:
        # Sử dụng cấu hình mặc định
        host = DEFAULT_HOST
        port = DEFAULT_PORT
        secret_key = DEFAULT_SECRET_KEY
        print("No configuration profile specified. Using default settings.")
    
    # Lặp lại việc gửi thông báo theo số lần chỉ định
    for i in range(args.repeat):
        message = args.message
        if args.repeat > 1:
            message = f"{args.message} (thông báo thứ {i+1})"
            print(f"Đang gửi thông báo {i+1}/{args.repeat}...")
        else:
            print(f"Đang gửi thông báo...")
            
        # Gửi thông báo tới server
        success = send_notification(
            message=message, 
            host=host, 
            control_port=port, 
            secret_key=secret_key
        )
        
        if success:
            print("Đã gửi thông báo thành công.")
        else:
            print("Gửi thông báo thất bại.")