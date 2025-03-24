import glob
import math
import os
import sys
import time
from pathlib import Path
from threading import Thread
from urllib.parse import urlparse
import cv2
import numpy as np
import torch
import re
from utils.logger_config import LOGGER

# Parameters
IMG_FORMATS = 'bmp', 'dng', 'jpeg', 'jpg', 'mpo', 'png', 'tif', 'tiff', 'webp', 'pfm'  # include image suffixes
VID_FORMATS = 'asf', 'avi', 'gif', 'm4v', 'mkv', 'mov', 'mp4', 'mpeg', 'mpg', 'ts', 'wmv'  # include video suffixes


def clean_str(s):
    # Cleans a string by replacing special characters with underscore _
    return re.sub(pattern="[|@#!¡·$€%&()=?¿^*;:,¨´><+]", repl="_", string=s)


def is_colab():
    # Is environment a Google Colab instance?
    return 'google.colab' in sys.modules


def is_kaggle():
    # Is environment a Kaggle Notebook?
    return os.environ.get('PWD') == '/kaggle/working' and os.environ.get('KAGGLE_URL_BASE') == 'https://www.kaggle.com'


class LoadImages:
    def __init__(self, path, vid_stride=1):
        files = []
        for p in sorted(path) if isinstance(path, (list, tuple)) else [path]:
            p = str(Path(p).resolve())
            if '*' in p:
                files.extend(sorted(glob.glob(p, recursive=True)))  # glob
            elif os.path.isdir(p):
                files.extend(sorted(glob.glob(os.path.join(p, '*.*'))))  # dir
            elif os.path.isfile(p):
                files.append(p)  # files
            else:
                raise FileNotFoundError(f'{p} does not exist')

        images = [x for x in files if x.split('.')[-1].lower() in IMG_FORMATS]
        videos = [x for x in files if x.split('.')[-1].lower() in VID_FORMATS]
        ni, nv = len(images), len(videos)

        self.files = images + videos
        self.nf = ni + nv  # number of files
        self.video_flag = [False] * ni + [True] * nv
        self.mode = 'image'
        self.vid_stride = vid_stride  # video frame-rate stride
        if any(videos):
            self._new_video(videos[0])  # new video
        else:
            self.cap = None
        assert self.nf > 0, f'No images or videos found in {p}. ' \
                            f'Supported formats are:\nimages: {IMG_FORMATS}\nvideos: {VID_FORMATS}'

    def __iter__(self):
        self.count = 0
        return self

    def __next__(self):
        if self.count == self.nf:
            raise StopIteration
        path = self.files[self.count]

        if self.video_flag[self.count]:
            # Read video
            self.mode = 'video'
            for _ in range(self.vid_stride):
                self.cap.grab()
            ret_val, im0 = self.cap.retrieve()
            while not ret_val:
                self.count += 1
                self.cap.release()
                if self.count == self.nf:  # last video
                    raise StopIteration
                path = self.files[self.count]
                self._new_video(path)
                ret_val, im0 = self.cap.read()

            self.frame += 1
            # im0 = self._cv2_rotate(im0)  # for use if cv2 autorotation is False
            s = f'video {self.count + 1}/{self.nf} ({self.frame}/{self.frames}) {path}: '

        else:
            # Read image
            self.count += 1
            im0 = cv2.imread(path)  # BGR
            assert im0 is not None, f'Image Not Found {path}'
            s = f'image {self.count}/{self.nf} {path}: '

        return path, im0, self.cap, s

    def _new_video(self, path):
        # Create a new video capture object
        self.frame = 0
        self.cap = cv2.VideoCapture(path)
        self.frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.vid_stride)
        self.orientation = int(self.cap.get(cv2.CAP_PROP_ORIENTATION_META))  # rotation degrees
        # self.cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)  # disable https://github.com/ultralytics/yolov5/issues/8493

    def _cv2_rotate(self, im):
        # Rotate a cv2 video manually
        if self.orientation == 0:
            return cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
        elif self.orientation == 180:
            return cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.orientation == 90:
            return cv2.rotate(im, cv2.ROTATE_180)
        return im

    def __len__(self):
        return self.nf  # number of files


class LoadStreams:
    def __init__(self, sources='streams.txt', vid_stride=1,
                 reconnect_attempts=10, reconnect_delay=5, timeout=30):
        torch.backends.cudnn.benchmark = True  # faster for fixed-size inference
        self.mode = 'stream'
        self.vid_stride = vid_stride  # video frame-rate stride
        
        # Thêm các tham số cho khả năng phục hồi
        self.reconnect_attempts = reconnect_attempts  # Số lần thử kết nối lại
        self.reconnect_delay = reconnect_delay  # Thời gian chờ giữa các lần kết nối lại (giây)
        self.timeout = timeout  # Timeout cho kết nối (giây)
        self.connection_status = []  # Trạng thái kết nối cho mỗi stream
        self.last_frame_time = []  # Thời gian nhận frame cuối cùng
        self.reconnecting = []  # Trạng thái đang thử kết nối lại
        
        sources = Path(sources).read_text().rsplit() if os.path.isfile(sources) else [sources]
        n = len(sources)
        self.sources = [clean_str(x) for x in sources]  # clean source names for later
        self.original_sources = sources.copy()  # Lưu lại URL gốc để kết nối lại khi cần
        self.imgs, self.fps, self.frames, self.threads = [None] * n, [0] * n, [0] * n, [None] * n
        self.connection_status = [True] * n  # Ban đầu giả định tất cả đều kết nối thành công
        self.last_frame_time = [time.time()] * n  # Thời gian nhận frame cuối
        self.reconnecting = [False] * n  # Không stream nào đang kết nối lại ban đầu
        self.caps = [None] * n  # Lưu lại các đối tượng VideoCapture
        
        for i, s in enumerate(sources):  # index, source
            # Start thread to read frames from video stream
            st = f'{i + 1}/{n}: {s}... '
            if urlparse(s).hostname in ('www.youtube.com', 'youtube.com', 'youtu.be'):  # if source is YouTube video
                # YouTube format i.e. 'https://www.youtube.com/watch?v=Zgi9g1ksQHc' or 'https://youtu.be/Zgi9g1ksQHc'
                # check_requirements(('pafy', 'youtube_dl==2020.12.2'))
                import pafy
                s = pafy.new(s).getbest(preftype="mp4").url  # YouTube URL
            s = eval(s) if s.isnumeric() else s  # i.e. s = '0' local webcam
            if s == 0:
                assert not is_colab(), '--source 0 webcam unsupported on Colab. Rerun command in a local environment.'
                assert not is_kaggle(), '--source 0 webcam unsupported on Kaggle. Rerun command in a local environment.'
            
            # Khởi tạo kết nối video
            success, cap = self.create_capture(s, i)
            
            if not success:
                LOGGER.warning(f'{st}Failed to open {s}. Will retry in background.')
                self.connection_status[i] = False
                self.imgs[i] = np.zeros((640, 640, 3), dtype=np.uint8)  # Tạo khung hình trống
            else:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)  # warning: may return 0 or nan
                LOGGER.info(f"Stream {i}: FPS: {fps}")

                self.frames[i] = max(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 0) or float('inf')  # infinite stream fallback
                self.fps[i] = max((fps if math.isfinite(fps) else 0) % 100, 0) or 30  # 30 FPS fallback

                _, self.imgs[i] = cap.read()  # guarantee first frame
                self.caps[i] = cap
                LOGGER.info(f"{st} Success ({self.frames[i]} frames {w}x{h} at {self.fps[i]:.2f} FPS)")
            
            # Luôn tạo thread, ngay cả khi kết nối ban đầu thất bại
            self.threads[i] = Thread(target=self.update, args=([i, cap, s]), daemon=True)
            self.threads[i].start()
                
    def create_capture(self, source, index):
        """Tạo và cấu hình VideoCapture với xử lý lỗi tốt hơn"""
        try:
            LOGGER.info(f"Attempting to connect to stream: {source}")
            cap = cv2.VideoCapture(source)
            
            # Thiết lập thông số kỹ thuật timeout cho RTSP, HTTP streams
            if isinstance(source, str) and ('rtsp:' in source or 'http:' in source or 'https:' in source):
                # Thiết lập timeouts
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.timeout * 1000)
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, self.timeout * 1000)
                # Một số camera yêu cầu buffer nhỏ để giảm độ trễ
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Thiết lập MJPG để đạt FPS cao
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            # Thiết lập độ phân giải và FPS
            desired_width = 2560
            desired_height = 1440
            desired_fps = 30

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, desired_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, desired_height)
            cap.set(cv2.CAP_PROP_FPS, desired_fps)
            
            # Verify connection
            if not cap.isOpened():
                LOGGER.error(f"Cannot open stream {index}: {source}")
                return False, None
                
            return True, cap
            
        except Exception as e:
            LOGGER.error(f"Error creating capture for stream {index}: {source}. Error: {str(e)}")
            return False, None
    
    def reconnect_stream(self, index, source):
        """Thử kết nối lại với stream"""
        if self.reconnecting[index]:
            return False, None  # Đã có thread đang thử kết nối lại
            
        self.reconnecting[index] = True
        LOGGER.warning(f"Attempting to reconnect to stream {index}: {source}")
        
        # Đóng kết nối cũ nếu còn tồn tại
        if self.caps[index] is not None:
            try:
                self.caps[index].release()
            except:
                pass
        
        # Thử kết nối lại với số lần thử xác định
        for attempt in range(self.reconnect_attempts):
            LOGGER.info(f"Reconnection attempt {attempt+1}/{self.reconnect_attempts} for stream {index}")
            success, cap = self.create_capture(source, index)
            
            if success and cap.isOpened():
                # Đọc frame đầu tiên để kiểm tra
                ret, frame = cap.read()
                if ret:
                    LOGGER.info(f"Successfully reconnected to stream {index}")
                    self.reconnecting[index] = False
                    self.connection_status[index] = True
                    self.last_frame_time[index] = time.time()
                    return True, cap
            
            # Chờ trước khi thử lại
            time.sleep(self.reconnect_delay)
        
        # Nếu tất cả các lần thử đều thất bại
        LOGGER.error(f"Failed to reconnect to stream {index} after {self.reconnect_attempts} attempts")
        self.reconnecting[index] = False
        return False, None

    def update(self, i, cap, stream):
        # Read stream `i` frames in daemon thread
        n, _ = 0, self.frames[i]  # frame number, frame array
        max_failures_before_reconnect = 5
        consecutive_failures = 0
        
        while True:  # Bỏ điều kiện dừng để luôn cố gắng duy trì kết nối
            try:
                if not self.connection_status[i]:
                    # Thử kết nối lại nếu mất kết nối
                    success, new_cap = self.reconnect_stream(i, self.original_sources[i])
                    if success:
                        cap = new_cap
                        self.caps[i] = cap
                        consecutive_failures = 0
                    else:
                        # Nếu không thể kết nối lại, chờ và thử lại
                        time.sleep(self.reconnect_delay)
                        continue
                
                # Kiểm tra xem kết nối có còn hoạt động không
                if cap is None or not cap.isOpened():
                    LOGGER.warning(f"Stream {i} connection lost. Attempting to reconnect...")
                    self.connection_status[i] = False
                    continue
                
                # Kiểm tra thời gian từ frame cuối cùng để phát hiện đóng băng
                current_time = time.time()
                if current_time - self.last_frame_time[i] > self.timeout and not self.reconnecting[i]:
                    LOGGER.warning(f"Stream {i} appears frozen (no frames for {self.timeout}s). Attempting to reconnect...")
                    self.connection_status[i] = False
                    continue
                
                # Đọc frame
                n += 1
                grab_success = cap.grab()  # .read() = .grab() followed by .retrieve()
                
                if not grab_success:
                    consecutive_failures += 1
                    LOGGER.warning(f"Failed to grab frame from stream {i}. Failure count: {consecutive_failures}/{max_failures_before_reconnect}")
                    
                    if consecutive_failures >= max_failures_before_reconnect:
                        LOGGER.warning(f"Stream {i} consistently failing. Attempting to reconnect...")
                        self.connection_status[i] = False
                        consecutive_failures = 0
                        continue
                    
                    # Chờ một chút trước khi thử lại
                    time.sleep(0.5)
                    continue
                
                # Reset bộ đếm lỗi nếu grab thành công
                consecutive_failures = 0
                
                # Chỉ xử lý mỗi vid_stride frame để giảm tải
                if n % self.vid_stride == 0:
                    success, im = cap.retrieve()
                    if success:
                        self.imgs[i] = im
                        self.last_frame_time[i] = time.time()  # Cập nhật thời gian frame cuối
                    else:
                        LOGGER.warning(f"WARNING ⚠️ Failed to retrieve frame from stream {i}")
                        # Không đặt ngay lập tức connection_status = False,
                        # cho phép một số lần thất bại trước khi thử kết nối lại
                        consecutive_failures += 1
                        if consecutive_failures >= max_failures_before_reconnect:
                            LOGGER.warning(f"Stream {i} consistently failing on retrieve. Attempting to reconnect...")
                            self.connection_status[i] = False
                            consecutive_failures = 0
                
                # Thêm short sleep để tránh đóng băng CPU
                time.sleep(0.001)
                
            except Exception as e:
                LOGGER.error(f"Error in stream {i} update: {str(e)}")
                self.connection_status[i] = False
                # Chờ trước khi thử lại để tránh vòng lặp lỗi quá nhanh
                time.sleep(1)

    def __iter__(self):
        self.count = -1
        return self

    def __next__(self):
        self.count += 1
        if not any(x.is_alive() for x in self.threads) or cv2.waitKey(1) == ord('q'):  # q to quit
            cv2.destroyAllWindows()
            raise StopIteration

        # Hiển thị trạng thái kết nối cho user
        for i, status in enumerate(self.connection_status):
            if not status and not self.reconnecting[i]:
                LOGGER.info(f"Stream {i} disconnected. Reconnection in progress...")
        
        # Tạo bản sao của hình ảnh hiện tại
        im0 = self.imgs.copy()
        
        # Thêm thông tin trạng thái kết nối
        connection_info = {i: {'status': self.connection_status[i], 
                              'reconnecting': self.reconnecting[i], 
                              'last_frame': self.last_frame_time[i]} 
                          for i in range(len(self.sources))}

        return self.sources, im0, None, connection_info

    def __len__(self):
        return len(self.sources)  # 1E12 frames = 32 streams at 30 FPS for 30 years
    
    def close(self):
        """Đóng tất cả các kết nối và giải phóng tài nguyên"""
        for i, cap in enumerate(self.caps):
            if cap is not None:
                cap.release()
        
        # Chờ tất cả các thread kết thúc
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
