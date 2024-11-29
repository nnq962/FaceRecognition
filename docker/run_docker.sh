#!/bin/bash

# Cấp quyền truy cập cho Docker
xhost +local:docker

# Chạy container face_detection
docker run -it \
    --rm \
    --device=/dev/video0 \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    nnq962/face_detection:latest

