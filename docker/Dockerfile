# Sử dụng image Python 3.10-slim làm base
FROM python:3.10-slim

# Cài đặt các gói hệ thống cần thiết cho OpenCV và Qt
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    gcc \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libx11-6 \
    libxcb1 \
    libx11-xcb1 \
    libxcb-glx0 \
    libxcb-keysyms1 \
    libxcb-image0 \
    libxcb-shm0 \
    libxcb-icccm4 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-util1 \
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libqt5gui5 \
    libqt5widgets5 \
    && rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Sao chép tệp requirements.txt vào container
COPY requirements.txt .

# Cài đặt các gói Python từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Thiết lập biến môi trường để sử dụng display của host
ENV DISPLAY=:0

# Thiết lập biến môi trường QT để chỉ định plugin path (tùy chọn)
ENV QT_XCB_GL_INTEGRATION=none

# Chạy ứng dụng khi container khởi động
CMD ["python", "main.py"]