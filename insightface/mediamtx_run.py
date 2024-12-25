import subprocess
import os
import sys
import signal

class MediaMTXController:
    def __init__(self):
        self.process = None
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.mediamtx_dir = os.path.join(self.current_dir, 'mediamtx_linux')
        self.mediamtx_executable = os.path.join(self.mediamtx_dir, 'mediamtx')

    def start(self):
        if self.process is not None:
            print("mediamtx đã chạy.")
            return

        if not os.path.isfile(self.mediamtx_executable):
            print(f"Không tìm thấy tệp thực thi mediamtx tại {self.mediamtx_executable}")
            sys.exit(1)

        if not os.access(self.mediamtx_executable, os.X_OK):
            print(f"Tệp thực thi mediamtx không có quyền thực thi. Đang cấp quyền thực thi...")
            os.chmod(self.mediamtx_executable, 0o755)

        command = [self.mediamtx_executable]

        try:
            self.process = subprocess.Popen(
                command,
                cwd=self.mediamtx_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            print("mediamtx đã được khởi chạy.")
            print("Đang theo dõi đầu ra của mediamtx...\n")

            while True:
                output = self.process.stdout.readline()
                if output:
                    print(output.strip())
                elif self.process.poll() is not None:
                    break

            rc = self.process.poll()
            print(f"mediamtx đã dừng với mã thoát {rc}")
            return rc

        except Exception as e:
            print(f"Đã xảy ra lỗi khi chạy mediamtx: {e}")
            sys.exit(1)

    def stop(self):
        if self.process is None:
            print("mediamtx không đang chạy.")
            return

        try:
            os.kill(self.process.pid, signal.SIGTERM)
            self.process.wait()
            print("mediamtx đã được dừng.")
            self.process = None
        except Exception as e:
            print(f"Đã xảy ra lỗi khi dừng mediamtx: {e}")

controller = MediaMTXController()
controller.start()