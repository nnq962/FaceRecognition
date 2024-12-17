import cv2

def record_webcam(output_path="output.mp4", fps=30, resolution=(640, 480), duration=10):
    """
    Open the webcam, display the video stream, and save it to an MP4 file.

    Args:
        output_path (str): Path to save the video file.
        fps (int): Frames per second of the saved video.
        resolution (tuple): Resolution of the video (width, height).
        duration (int): Duration to record the video in seconds.
    """
    # Open the default webcam (index 0)
    cap = cv2.VideoCapture(0)

    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

    # Define the codec and create a VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for MP4
    out = cv2.VideoWriter(output_path, fourcc, fps, resolution)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print(f"Recording video to '{output_path}' at {fps} FPS for {duration} seconds...")
    frame_count = 0
    total_frames = fps * duration  # Total number of frames to record

    while cap.isOpened():
        ret, frame = cap.read()  # Read a frame from the webcam
        if not ret:
            print("Error: Failed to capture frame.")
            break

        # Write the frame to the output file
        out.write(frame)

        # Display the frame in a window
        cv2.imshow("Webcam Recording", frame)

        # Stop recording after the specified duration
        frame_count += 1
        if frame_count >= total_frames:
            print("Recording completed.")
            break

        # Press 'q' to stop recording early
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Recording stopped by user.")
            break

    # Release resources
    cap.release()
    out.release()
    cv2.destroyAllWindows()

# Call the function
record_webcam(output_path="recorded_video.mp4", fps=30, resolution=(640, 480), duration=10)