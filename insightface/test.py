import asyncio
from insightface_detector_webrtc import InsightFaceDetector
from media_manager import MediaManager

async def main():
    # Tạo media manager và detector
    media_manager = MediaManager(
        source='0',
        save=False,
        face_recognition=True,
        face_emotion=False,
        check_small_face=False,
        streaming=False,
        export_data=False,
        time_to_save=5,
        show_time_process=False,
        raise_hand=False,
        view_img=True
    )

    detector = InsightFaceDetector(media_manager=media_manager)

    # Chạy WebRTC server và inference song song
    await asyncio.gather(
        detector.run_webrtc_server(),
        detector.run_inference()
    )


if __name__ == "__main__":
    asyncio.run(main())