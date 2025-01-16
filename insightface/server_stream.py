import json
import queue
from av import VideoFrame
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiohttp import web
import aiohttp_cors
from fractions import Fraction
import time
import cv2
import asyncio

# Hàng đợi toàn cục để lưu frame
frame_queue = queue.Queue(maxsize=600)

class OpenCVVideoStreamTrack(MediaStreamTrack):
    """
    A video track that streams frames from webcam.
    """
    kind = "video"

    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)  # Mở webcam
        if not self.cap.isOpened():
            raise RuntimeError("Không thể mở webcam.")

    async def recv(self):
        # Đọc frame từ webcam
        ret, frame = self.cap.read()
        if not ret:
            print("Không thể đọc frame từ webcam.")
            return

        # Chuyển frame thành VideoFrame
        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = time.time_ns() // 1000  # Presentation timestamp
        video_frame.time_base = Fraction(1, 1000000)  # Microseconds

        await asyncio.sleep(1 / 30)  # Đặt tốc độ khung hình (30 FPS)
        return video_frame


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    print("PeerConnection created")

    # Thêm track video từ lớp OpenCVVideoStreamTrack
    video_track = OpenCVVideoStreamTrack()
    pc.addTrack(video_track)
    print("Added OpenCV video track")

    # Handle the offer
    await pc.setRemoteDescription(offer)
    print("Set remote description")
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    print("Set local description")

    print("Answer created and sent to client")
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def index(request):
    """
    Serve the client HTML file for accessing the video stream.
    """
    with open("client_test.html", "r") as f:
        content = f.read()
    return web.Response(content_type="text/html", text=content)


if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", index)  # Route để phục vụ HTML
    app.router.add_post("/offer", offer)

    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    for route in app.router.routes():
        cors.add(route)

    # Chạy WebRTC server
    web.run_app(app, host="0.0.0.0", port=9090)