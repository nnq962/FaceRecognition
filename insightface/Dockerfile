# 1. Sử dụng base image của NVIDIA có sẵn CUDA 12.2 và cuDNN 8 trên Ubuntu 22.04
FROM nvidia/cuda:12.6.3-cudnn-devel-ubuntu22.04

# 3. Cài đặt các dependencies cần thiết
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    git \
    curl \
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
    supervisor \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 4. Cài gdown để tải model từ Google Drive
RUN pip3 install --no-cache-dir gdown

# 5. Tạo thư mục chứa model và tải các model
RUN mkdir -p /root/Models

RUN gdown --id 1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X -O /root/Models/det_10g.onnx && \
    gdown --id 1JKwOYResiJf7YyixHCizanYmvPrl1bP2 -O /root/Models/w600k_r50.onnx && \
    gdown --id 1zmW9g7vaRWuFSUKIS9ShCmP-6WU6Xxan -O /root/Models/GFPGANv1.3.pth && \
    gdown --id 1jP3-UU8LhBvG8ArZQNl6kpDUfH_Xan9m -O /root/Models/detection_Resnet50_Final.pth && \
    gdown --id 1ZFqra3Vs4i5fB6B8LkyBo_WQXaPRn77y -O /root/Models/parsing_parsenet.pth

# 6. Nâng cấp pip, setuptools, wheel
RUN python3 -m pip install --upgrade pip setuptools wheel

# 7. Thiết lập thư mục làm việc
WORKDIR /app

# 8. Sao chép file requirements và cài đặt
COPY requirements_linux.txt .
RUN pip3 install --no-cache-dir -r requirements_linux.txt

# 9. Sao chép toàn bộ mã nguồn vào container
COPY . .

# 10. Thiết lập biến môi trường hiển thị, nếu cần giao diện
ENV DISPLAY=:0
ENV QT_XCB_GL_INTEGRATION=none

# 11. Chạy Flask (hoặc script chính) khi container start
ENTRYPOINT ["python3", "main_docker.py"]
