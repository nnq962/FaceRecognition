# InsightFaceDetector Project

## Introduction
The **InsightFaceDetector** project is an advanced image detection and analysis system that integrates multiple functionalities, including face recognition, emotion analysis, hand-raising detection, and QR/ArUco code detection. It is designed to process data from static images, videos, or webcam streams, making it suitable for applications such as automated attendance tracking, behavior monitoring, and real-time data analysis.

## Key Features
1. **Face Recognition**  
   - Utilizes the InsightFace model for high-accuracy face detection and recognition.  
   - Generates face embeddings and compares them with a database for identity verification.  

2. **Face Emotion Analysis**  
   - Analyzes facial emotions (e.g., happy, sad, angry) based on detected faces.  

3. **Hand-Raising Detection**  
   - Detects hand-raising actions of individuals within the frame.  

4. **QR/ArUco Code Detection**  
   - Detects and decodes ArUco markers to support tasks like attendance or verification.  

5. **Automated Attendance Tracking**  
   - Logs individual presence based on face recognition and stores data by date.  

6. **Cross-Platform Support**  
   - Runs on Linux, Windows, and other operating systems using OpenCV and related libraries.  

## Technologies Used
- **Programming Language**: Python  
- **Main Libraries**:  
  - `OpenCV (cv2)`: Image and video processing.  
  - `InsightFace`: Face detection and recognition.  
  - `Ultralytics YOLO`: Object detection (if integrated).  
  - `onnxruntime`: Efficient ONNX model execution.  
  - `numpy`: Numerical data processing.  
- **Models**:  
  - `Retinaface`: Face detection model.  
  - `Arcface`: Face recognition model.  
- **Hardware Support**: Optimized for CPU and GPU (InsightFace).  

## Installation
1. **Requirements**:  
   - Python 3.10+  
   - Libraries: `opencv-python`, `insightface`, `ultralytics`, `onnxruntime`, `numpy`  
   - Optional: GPU (CUDA) for accelerated processing.  

2. **Install Dependencies**:  
   ```bash  
   pip install -r requirements.txt  