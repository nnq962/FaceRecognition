# Payton Shaltis
# Hand Position Detection
# ---
# Prints the current position of each of the user's hands (either raised or 
# lowered) based on the wrist and shoulder landmarks using MediaPipe Pose.
# Based on the supplied sample. New code is indicated with comments.

import cv2
import mediapipe as mp
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

# --- NEWLY ADDED CODE START --- #

# Variables for tracking arm positions
landmarks_formed = False
right_hand_raised = False
left_hand_raised = False

# --- NEWLY ADDED CODE END --- #

# For webcam input:
cap = cv2.VideoCapture(0)
with mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5) as pose:
  while cap.isOpened():
    success, image = cap.read()
    if not success:
      print("Ignoring empty camera frame.")
      # If loading a video, use 'break' instead of 'continue'.
      continue

    # To improve performance, optionally mark the image as not writeable to
    # pass by reference.
    image.flags.writeable = False
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image)

    # --- NEWLY ADDED CODE START --- #

    # If the landmarks can be formed (person detected)...
    if(results.pose_landmarks):
      
      # Indicate that a user has been detected.
      if(not landmarks_formed):
        landmarks_formed = True
        print("Person detected. Begin arm movements.")

      # Store importnat landmarks
      right_shoulder = results.pose_landmarks.landmark[12]
      right_wrist = results.pose_landmarks.landmark[16]
      left_shoulder = results.pose_landmarks.landmark[11]
      left_wrist = results.pose_landmarks.landmark[15]

      # If the right wrist raises above the right shoulder, it is raised.
      if(right_wrist.y < right_shoulder.y and not right_hand_raised):
        print("Right hand raised")
        right_hand_raised = True

      # If the right wrist falls below the right shoulder, it is lowered.
      if(right_wrist.y > right_shoulder.y and right_hand_raised):
          print("Right hand lowered")
          right_hand_raised = False
      
      # If the left wrist raises above the left shoulder, it is raised.
      if(left_wrist.y < left_shoulder.y and not left_hand_raised):
        print("Left hand raised")
        left_hand_raised = True

      # If the left wrist falls below the left shoulder, it is lowered.
      if(left_wrist.y > left_shoulder.y and left_hand_raised):
          print("Left hand lowered")
          left_hand_raised = False
    
    # If landmarks cannot be formed (no person detected)...
    elif(landmarks_formed):
      landmarks_formed = False
      print("No person detected. Please re-enter the frame.")

    # --- NEWLY ADDED CODE END --- #

    # Draw the pose annotation on the image.
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    mp_drawing.draw_landmarks(
      image,
      results.pose_landmarks,
      mp_pose.POSE_CONNECTIONS,
      landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())
    # Flip the image horizontally for a selfie-view display.
    cv2.imshow('MediaPipe Pose', cv2.flip(image, 1))
    if cv2.waitKey(5) & 0xFF == 27:
      break
cap.release()