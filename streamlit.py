import os
import logging
import cv2
import numpy as np
from ultralytics import YOLO
import streamlit as st
from pathlib import Path
from moviepy.editor import ImageSequenceClip

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load YOLO models
yolo_models = {
    'regular_deadlift': YOLO("muscleAi_weights/best.pt"),
    'sumo_deadlift': YOLO("muscleAi_weights/sumo_best.pt"),
    'squat': YOLO("muscleAi_weights/squats_best.pt"),
    'romanian_deadlift': YOLO("muscleAi_weights/best_romanian.pt"),
    "zercher_squat": YOLO("muscleAi_weights/zercher_best.pt"),
    "front_squat": YOLO("muscleAi_weights/front_squats_best.pt")
}

# Function to check for injury risk (unchanged)
def check_injury_risk(labels, exercise_type):
    if exercise_type in ['regular_deadlift', 'squat']:
        ibw_value = labels.get('ibw', 1.0)
        down_value = labels.get('down', 1.0)
    else:
        ibw_value = labels.get('up', 1.0)
        down_value = labels.get('down', 1.0)

    return "stop right now to prevent injury" if ibw_value < 0.80 or down_value < 0.70 else "No significant risk"

# Function to draw keypoints on the frame (unchanged)
def draw_keypoints(frame, keypoints):
    for point in keypoints:
        x, y = int(point[0]), int(point[1])
        cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
    return frame

# Function to process video with YOLO
def process_video_with_yolo(video_path, exercise_type):
    processed_frames = []
    
    yolo_model = yolo_models[exercise_type]
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        st.error("Error opening video file")
        return None

    # Get original video FPS
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30  # fallback value

    last_ibw_label = None
    rep_count = 0
    rep_started = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        results = yolo_model(source=frame, stream=True, conf=0.3)
        
        for result in results:
            frame = result.orig_img
            
            labels = {result.names[int(box.cls)]: float(box.conf) for box in result.boxes} if result.boxes is not None else {}
            injury_risk = check_injury_risk(labels, exercise_type)

            current_ibw_label = labels.get('ibw') if exercise_type in ['regular_deadlift', 'squat'] else labels.get('up')
            
            if last_ibw_label is not None and current_ibw_label is not None:
                if not rep_started:
                    if last_ibw_label > 0.89 and current_ibw_label <= 0.89:
                        rep_started = True
                else:
                    if last_ibw_label <= 0.89 and current_ibw_label > 0.89:
                        rep_count += 1
                        rep_started = False

            last_ibw_label = current_ibw_label

            if hasattr(result, 'keypoints') and result.keypoints is not None:
                keypoints = result.keypoints.xy[0]
                frame = draw_keypoints(frame, keypoints)

            cv2.putText(frame, f"Injury Risk: {injury_risk}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, f"Repetitions: {rep_count}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Convert BGR to RGB for MoviePy
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            processed_frames.append(frame_rgb)

    cap.release()
    
    return processed_frames, fps

# Streamlit UI
st.title("Aligno")

exercise_type = st.selectbox("Select Exercise Type", list(yolo_models.keys()))

uploaded_file = st.file_uploader("Upload a Video", type=["mp4", "mov"])

if uploaded_file is not None:
    # Create directories if they don't exist
    video_dir = Path('./videos')
    processed_dir = Path('./processed_videos')
    
    video_dir.mkdir(exist_ok=True)
    processed_dir.mkdir(exist_ok=True)

    # Save uploaded video
    video_path = video_dir / uploaded_file.name
    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.button("Process Video"):
        with st.spinner('Processing video...'):
            # Process the video
            processed_frames, fps = process_video_with_yolo(str(video_path), exercise_type)

            if processed_frames is not None:
                # Generate output path
                output_filename = f'processed_{Path(uploaded_file.name).stem}.mp4'
                output_video_path = processed_dir / output_filename
                
                try:
                    # Create video using MoviePy
                    clip = ImageSequenceClip(processed_frames, fps=fps)
                    
                    # Write video with good quality
                    clip.write_videofile(
                        str(output_video_path),
                        codec='libx264',
                        fps=fps,
                        preset='medium',
                        bitrate='8000k',
                        audio=False
                    )
                    
                    # Read the processed video for display
                    with open(output_video_path, 'rb') as video_file:
                        video_bytes = video_file.read()
                    
                    # Display the processed video
                    st.success("Video processed successfully!")
                    st.video(video_bytes)
                    
                except Exception as e:
                    st.error(f"Error creating video: {str(e)}")
                finally:
                    # Clean up MoviePy clip
                    if 'clip' in locals():
                        clip.close()

def process_live_video(exercise_type):
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("Error opening webcam")
        return

    # Create placeholder for video frame
    stframe = st.empty()
    
    # Create placeholders for metrics
    metrics_placeholder = st.empty()
    
    last_ibw_label = None
    rep_count = 0
    rep_started = False
    
    stop_button = st.button("Stop Stream")

    while not stop_button:
        ret, frame = cap.read()
        if not ret:
            st.error("Error reading from webcam")
            break
        
        results = yolo_models[exercise_type](source=frame, stream=True, conf=0.3)
        
        for result in results:
            frame = result.orig_img
            
            labels = {result.names[int(box.cls)]: float(box.conf) for box in result.boxes} if result.boxes is not None else {}
            injury_risk = check_injury_risk(labels, exercise_type)

            current_ibw_label = labels.get('ibw') if exercise_type in ['regular_deadlift', 'squat'] else labels.get('up')
            
            if last_ibw_label is not None and current_ibw_label is not None:
                if not rep_started:
                    if last_ibw_label > 0.89 and current_ibw_label <= 0.89:
                        rep_started = True
                else:
                    if last_ibw_label <= 0.89 and current_ibw_label > 0.89:
                        rep_count += 1
                        rep_started = False

            last_ibw_label = current_ibw_label

            # Draw keypoints if available
            if hasattr(result, 'keypoints') and result.keypoints is not None:
                keypoints = result.keypoints.xy[0]
                frame = draw_keypoints(frame, keypoints)

            # Convert BGR to RGB for Streamlit
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Update frame
            stframe.image(frame_rgb, channels="RGB", use_column_width=True)
            
            # Update metrics
            metrics_placeholder.text(f"Injury Risk: {injury_risk}\nRepetitions: {rep_count}")

    cap.release()

if st.button("Start Live Stream"):
    process_live_video(exercise_type)
