import asyncio
import json
import logging
import os
import time
from fractions import Fraction

import cv2
from aiohttp import web
from av import VideoFrame
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer
import aiohttp_cors  # Import thư viện CORS

# Global variables for managing peer connections
pcs = set()
ROOT = os.path.dirname(__file__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pc")

class OpenCVVideoStreamTrack(MediaStreamTrack):
    """
    A video track that reads frames from an OpenCV video source.
    """
    kind = "video"

    def __init__(self, source=0):
        super().__init__()
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise Exception("Could not open video source: {}".format(source))

    async def recv(self):
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Failed to read frame from OpenCV source")

        # Convert frame to VideoFrame
        new_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        new_frame.pts = time.time_ns() // 1000  # Presentation timestamp
        new_frame.time_base = Fraction(1, 1000000)  # Microseconds

        return new_frame

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)
    logger.info("PeerConnection created")

    logger.info("Client SDP offer: %s", offer.sdp)

    # Parse SDP to determine if client expects audio or video
    sdp = offer.sdp
    # expects_audio = "m=audio" in sdp
    expects_video = "m=video" in sdp

    if expects_video:
        # Add video track if client expects video
        video_track = OpenCVVideoStreamTrack(source=0)  # Webcam
        pc.addTrack(video_track)
        logger.info("Added OpenCV video track")

    # if expects_audio:
    #     # Add audio track if client expects audio
    #     audio_player = MediaPlayer(os.path.join(ROOT, "demo-instruct.wav"))
    #     pc.addTrack(audio_player.audio)
    #     logger.info("Added audio track")

    # Handle the offer
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    logger.info("Server SDP answer: %s", answer.sdp)
    await pc.setLocalDescription(answer)

    logger.info("Answer created and sent to client")
    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    """
    Cleanup peer connections on shutdown.
    """
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

    
async def index(request):
    """
    Serve the client HTML file for accessing the video stream.
    """
    with open("templates/webrtc_client.html", "r") as f:
        content = f.read()
    return web.Response(content_type="text/html", text=content)


import ssl

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", index)  # Route để phục vụ HTML
    app.router.add_post("/offer", offer)

    app.on_shutdown.append(on_shutdown)

    # Configure SSL context for HTTPS
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile="cert_and_key/cert.pem", keyfile="cert_and_key/key.pem")

    # Run the app with HTTPS
    web.run_app(app, host="0.0.0.0", port=9090, ssl_context=ssl_context)