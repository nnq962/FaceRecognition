

import time
import threading
import torch
import contextlib

class Profile:
    def __init__(self):
        self.cuda = torch.cuda.is_available()
        self.start = self.time()
        self.timer_thread = None
        self.running = False
        self.interval = 5.0  # Mặc định 5 giây
        
    def reset(self):
        self.start = self.time()
        
    def elapsed(self):
        return self.time() - self.start
        
    def time(self):
        if self.cuda:
            torch.cuda.synchronize()
        return time.time()
    
    def start_periodic_task(self, task_func, interval=5.0):
        """
        Bắt đầu một tác vụ định kỳ mỗi interval giây
        
        :param task_func: Hàm cần chạy định kỳ
        :param interval: Khoảng thời gian giữa các lần chạy (giây)
        """
        self.interval = interval
        self.task_func = task_func
        self.running = True
        self.timer_thread = threading.Thread(target=self._run_periodic)
        self.timer_thread.daemon = True
        self.timer_thread.start()
        return self
    
    def stop_periodic_task(self):
        """Dừng tác vụ định kỳ"""
        self.running = False
        if self.timer_thread:
            self.timer_thread.join(timeout=1.0)
        return self
    
    def _run_periodic(self):
        """Chạy tác vụ định kỳ"""
        while self.running:
            time.sleep(self.interval)
            self.task_func()
    
    @contextlib.contextmanager
    def timer(self, name=None):
        """Context manager để đo thời gian của một block code"""
        start = self.time()
        yield
        end = self.time()
        elapsed = end - start
        if name:
            print(f"{name}: {elapsed:.6f} giây")
        else:
            print(f"Thời gian thực thi: {elapsed:.6f} giây")



# Khởi tạo
prof = Profile()

# Đo thời gian đơn giản
prof.reset()
# Thực hiện một số tác vụ
time.sleep(10)  # Giả lập tác vụ
print(f"Thời gian đã trôi qua: {prof.elapsed():.6f} giây")

# Sử dụng context manager để đo thời gian
with prof.timer("Tác vụ A"):
    time.sleep(5)  # Giả lập tác vụ

# Chạy một tác vụ định kỳ mỗi 5 giây
def send_data():
    print(f"Đang gửi dữ liệu... (Thời gian: {prof.elapsed():.2f}s)")

# Bắt đầu tác vụ định kỳ
prof.start_periodic_task(send_data, interval=5.0)

# Tiếp tục với công việc khác
time.sleep(40)  # Để tác vụ định kỳ chạy trong 20 giây

# Dừng tác vụ định kỳ
prof.stop_periodic_task()