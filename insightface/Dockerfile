# Định nghĩa image cơ bản và kiến trúc
ARG IMAGE_NAME
FROM ${IMAGE_NAME}:12.6.3-runtime-ubuntu22.04 as base

# Tùy chỉnh cho kiến trúc amd64
FROM base as base-amd64
ENV NV_CUDNN_VERSION 9.5.1.17-1
ENV NV_CUDNN_PACKAGE_NAME libcudnn9-cuda-12
ENV NV_CUDNN_PACKAGE libcudnn9-cuda-12=${NV_CUDNN_VERSION}

# Tùy chỉnh cho kiến trúc arm64
FROM base as base-arm64
ENV NV_CUDNN_VERSION 9.5.1.17-1
ENV NV_CUDNN_PACKAGE_NAME libcudnn9-cuda-12
ENV NV_CUDNN_PACKAGE libcudnn9-cuda-12=${NV_CUDNN_VERSION}

# Lựa chọn kiến trúc phù hợp
FROM base-${TARGETARCH}

# Định nghĩa biến kiến trúc
ARG TARGETARCH

# Metadata
LABEL maintainer="NVIDIA CORPORATION <cudatools@nvidia.com>"
LABEL com.nvidia.cudnn.version="${NV_CUDNN_VERSION}"

# Cài đặt cuDNN
RUN apt-get update && apt-get install -y --no-install-recommends \
    ${NV_CUDNN_PACKAGE} \
    && apt-mark hold ${NV_CUDNN_PACKAGE_NAME} \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt các dependencies hệ thống cần thiết
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

# Cài đặt gdown để tải model từ Google Drive
RUN pip install --no-cache-dir gdown

# Tạo thư mục lưu trữ model
RUN mkdir -p /root/Models

# Tải các mô hình từ Google Drive
RUN gdown --id 1j47suEUpM6oNAgNvI5YnaLSeSnh1m45X -O /root/Models/det_10g.onnx && \
    gdown --id 1JKwOYResiJf7YyixHCizanYmvPrl1bP2 -O /root/Models/w600k_r50.onnx && \
    gdown --id 1zmW9g7vaRWuFSUKIS9ShCmP-6WU6Xxan -O /root/Models/GFPGANv1.3.pth && \
    gdown --id 1jP3-UU8LhBvG8ArZQNl6kpDUfH_Xan9m -O /root/Models/detection_Resnet50_Final.pth && \
    gdown --id 1ZFqra3Vs4i5fB6B8LkyBo_WQXaPRn77y -O /root/Models/parsing_parsenet.pth

# Tối ưu hóa pip
RUN python3 -m pip install --upgrade pip setuptools wheel

# Thiết lập thư mục làm việc
WORKDIR /app

# Sao chép tệp requirements.txt vào container
COPY requirements.txt .

# Cài đặt các gói Python từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Thiết lập biến môi trường để sử dụng display của host
ENV DISPLAY=:0

# Thiết lập biến môi trường QT để chỉ định plugin path
ENV QT_XCB_GL_INTEGRATION=none

# Thiết lập CMD để chạy Flask app, hỗ trợ truyền tham số qua argparse
ENTRYPOINT ["python3", "main_docker.py"]
