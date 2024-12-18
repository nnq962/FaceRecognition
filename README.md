# **3HINC_FaceRecognition**

A powerful face recognition and emotion detection system built with state-of-the-art models and tools. This project enables real-time video processing, streaming to RTSP endpoints, and advanced face analysis using Python and popular libraries like PyTorch and OpenCV.

---

## **Table of Contents**
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Folder Structure](#folder-structure)
- [Contributing](#contributing)
- [License](#license)

---

## **Features**
✨ Key functionalities of the project:
- **Real-Time Face Recognition**: Detect and identify faces from video or webcam streams.
- **Emotion Detection**: Analyze facial expressions and determine emotions.
- **Stream to RTSP**: Push processed video streams to RTSP endpoints using FFmpeg.
- **Integration with MediaMTX**: Compatible with MediaMTX for scalable video streaming.
- **Flexible Configuration**: Easily customize detection thresholds, streaming options, and output formats.

---

## **Installation**
Follow these steps to set up the project:

### Prerequisites
- **Python 3.10+**
- **FFmpeg** installed on your system.
- **MediaMTX** (optional for RTSP streaming).

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/3HINC_FaceRecognition.git
   cd 3HINC_FaceRecognition
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv myenv
   source myenv/bin/activate  # On Windows, use `myenv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install and configure MediaMTX (if streaming is required):
   - Refer to [MediaMTX setup](https://github.com/bluenviron/mediamtx).

---

## **Usage**
### Run Face Recognition
To start the system with real-time face detection and emotion analysis:
```bash
python main.py --source 0 --streaming
```

### RTSP Streaming
Make sure MediaMTX is running and configured properly. Push streams to RTSP endpoints:
- Example for `stream1`:
  ```bash
  ffmpeg -re -i input.mp4 -c:v libx264 -f rtsp rtsp://localhost:8554/stream1
  ```

### Additional Options
- **Custom Input**: Use video files, images, or webcams by specifying `--source`.
- **Save Outputs**: Enable saving processed images/videos using `--save-img` or `--save-video`.

---

## **Configuration**
Modify settings in the project or command-line arguments:
- `--source`: Input source (webcam ID, video file path, or RTSP URL).
- `--streaming`: Enable RTSP streaming.
- `--save-img`: Save annotated images locally.
- `--face-emotion`: Enable emotion detection.

---

## **Folder Structure**
Here’s an overview of the project structure:

```
3HINC_FaceRecognition/
│
├── insightface/                  # Core face recognition modules
│   ├── media_manager.py          # Handles video streaming and FFmpeg
│   ├── insightface_detector.py   # Face detection and emotion analysis
│
├── yolov9/                       # YOLOv9-related modules (if any)
│
├── requirements.txt              # Python dependencies
├── README.md                     # Project documentation
├── main.py                       # Main entry point
└── mediamtx.yml                  # Configuration for MediaMTX
```

---

## **Contributing**
We welcome contributions! Here’s how you can help:
1. Fork the repository.
2. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b my-feature-branch
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add my feature"
   ```
4. Push to your branch and submit a pull request.

---

## **License**
This project is licensed under the [MIT License](LICENSE).

---

## **Screenshots**
![Face Detection Example](https://via.placeholder.com/800x400?text=Add+your+screenshot+here)

---
