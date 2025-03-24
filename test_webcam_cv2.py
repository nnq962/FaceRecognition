import cv2
import time

def get_webcam_properties(cap):
    # Danh sách các thuộc tính của webcam để kiểm tra
    prop_list = {
        'CAP_PROP_POS_MSEC': cv2.CAP_PROP_POS_MSEC,
        'CAP_PROP_POS_FRAMES': cv2.CAP_PROP_POS_FRAMES,
        'CAP_PROP_POS_AVI_RATIO': cv2.CAP_PROP_POS_AVI_RATIO,
        'CAP_PROP_FRAME_WIDTH': cv2.CAP_PROP_FRAME_WIDTH,
        'CAP_PROP_FRAME_HEIGHT': cv2.CAP_PROP_FRAME_HEIGHT,
        'CAP_PROP_FPS': cv2.CAP_PROP_FPS,
        'CAP_PROP_FOURCC': cv2.CAP_PROP_FOURCC,
        'CAP_PROP_FRAME_COUNT': cv2.CAP_PROP_FRAME_COUNT,
        'CAP_PROP_FORMAT': cv2.CAP_PROP_FORMAT,
        'CAP_PROP_MODE': cv2.CAP_PROP_MODE,
        'CAP_PROP_BRIGHTNESS': cv2.CAP_PROP_BRIGHTNESS,
        'CAP_PROP_CONTRAST': cv2.CAP_PROP_CONTRAST,
        'CAP_PROP_SATURATION': cv2.CAP_PROP_SATURATION,
        'CAP_PROP_HUE': cv2.CAP_PROP_HUE,
        'CAP_PROP_GAIN': cv2.CAP_PROP_GAIN,
        'CAP_PROP_EXPOSURE': cv2.CAP_PROP_EXPOSURE,
        'CAP_PROP_CONVERT_RGB': cv2.CAP_PROP_CONVERT_RGB,
        'CAP_PROP_WHITE_BALANCE_BLUE_U': cv2.CAP_PROP_WHITE_BALANCE_BLUE_U,
        'CAP_PROP_WHITE_BALANCE_RED_V': cv2.CAP_PROP_WHITE_BALANCE_RED_V,
        'CAP_PROP_ISO_SPEED': cv2.CAP_PROP_ISO_SPEED,
        'CAP_PROP_BUFFERSIZE': cv2.CAP_PROP_BUFFERSIZE,
        'CAP_PROP_AUTOFOCUS': cv2.CAP_PROP_AUTOFOCUS,
        'CAP_PROP_ZOOM': cv2.CAP_PROP_ZOOM
    }

    # Thu thập tất cả thông tin có thể từ camera
    properties = {}
    for prop_name, prop_id in prop_list.items():
        value = cap.get(prop_id)
        properties[prop_name] = value

    # Xử lý đặc biệt với FOURCC để hiển thị định dạng
    fourcc = properties.get('CAP_PROP_FOURCC', 0)
    fourcc_str = ''.join([chr((int(fourcc) >> (i * 8)) & 0xFF) for i in range(4)])
    properties['CAP_PROP_FOURCC_STR'] = fourcc_str

    return properties

def measure_actual_fps(cap, num_frames=100):
    # Đo FPS thực tế
    start = time.time()
    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            break
    end = time.time()
    elapsed = end - start
    actual_fps = num_frames / elapsed if elapsed > 0 else 0
    return actual_fps

def test_supported_resolutions(device_id=0):
    # Danh sách các độ phân giải phổ biến để thử nghiệm
    resolutions = [
        (320, 240),
        (640, 480),
        (800, 600),
        (1024, 768),
        (1280, 720),
        (1280, 960),
        (1440, 1080),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160)
    ]

    supported_resolutions = []
    
    for width, height in resolutions:
        cap = cv2.VideoCapture(device_id)
        if not cap.isOpened():
            print(f"Không thể mở camera với ID {device_id}")
            cap.release()
            break
            
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Đọc một khung hình để xác nhận
        ret, frame = cap.read()
        if ret:
            actual_frame_width = frame.shape[1]
            actual_frame_height = frame.shape[0]
            
            if (actual_width, actual_height) not in supported_resolutions:
                supported_resolutions.append((actual_width, actual_height))
            
            print(f"Thử nghiệm độ phân giải {width}x{height}:")
            print(f"  - Độ phân giải đã cài đặt: {actual_width}x{actual_height}")
            print(f"  - Kích thước khung hình thực tế: {actual_frame_width}x{actual_frame_height}")
        
        cap.release()
    
    return supported_resolutions

def main():
    print("===== THÔNG TIN CHI TIẾT WEBCAM BẰNG OPENCV =====")
    
    # Danh sách các camera có thể kết nối
    print("\n===== KIỂM TRA CÁC CAMERA CÓ THỂ KẾT NỐI =====")
    available_cameras = []
    for i in range(5):  # Thử với 5 ID camera đầu tiên
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    
    print(f"Cameras có sẵn: {available_cameras}")
    
    # Mặc định sử dụng camera đầu tiên
    camera_id = 0 if available_cameras else -1
    
    if camera_id >= 0:
        # Thử nghiệm độ phân giải hỗ trợ
        print("\n===== CÁC ĐỘ PHÂN GIẢI ĐƯỢC HỖ TRỢ =====")
        supported_resolutions = test_supported_resolutions(camera_id)
        print(f"\nTổng hợp các độ phân giải được hỗ trợ: {supported_resolutions}")
        
        # Kiểm tra các thuộc tính
        print("\n===== THÔNG TIN CHI TIẾT CAMERA =====")
        cap = cv2.VideoCapture(camera_id)
        if cap.isOpened():
            properties = get_webcam_properties(cap)
            
            # In thông tin chung
            width = int(properties['CAP_PROP_FRAME_WIDTH'])
            height = int(properties['CAP_PROP_FRAME_HEIGHT'])
            fps = properties['CAP_PROP_FPS']
            
            print(f"Độ phân giải: {width}x{height}")
            print(f"FPS (theo API): {fps}")
            
            # Đo FPS thực tế
            actual_fps = measure_actual_fps(cap, 30)
            print(f"FPS (đo thực tế với 30 frames): {actual_fps:.2f}")
            
            # In tất cả thuộc tính
            print("\nTất cả thuộc tính camera:")
            for prop, value in properties.items():
                print(f"{prop}: {value}")
            
            # Hiển thị video từ camera
            print("\n===== HIỂN THỊ VIDEO TỪ CAMERA =====")
            print("Nhấn 'q' để thoát khỏi video")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Hiển thị thông tin trên khung hình
                frame_info = f"Resolution: {frame.shape[1]}x{frame.shape[0]}, FPS: {actual_fps:.2f}"
                cv2.putText(frame, frame_info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow('Webcam', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
        else:
            print(f"Không thể mở camera với ID {camera_id}")
    else:
        print("Không tìm thấy camera nào kết nối.")
    
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()