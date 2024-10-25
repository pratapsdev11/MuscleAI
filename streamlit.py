import os
import logging
import cv2
from ultralytics import YOLO
import streamlit as st

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

# Function to check for injury risk
def check_injury_risk(labels, exercise_type):
    if exercise_type in ['regular_deadlift', 'squat']:
        ibw_value = labels.get('ibw', 1.0)
        down_value = labels.get('down', 1.0)
    else:
        ibw_value = labels.get('up', 1.0)
        down_value = labels.get('down', 1.0)

    return "stop right now to prevent injury" if ibw_value < 0.80 or down_value < 0.70 else "No significant risk"

# Function to draw keypoints on the frame
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

            # Draw keypoints on the frame if available
            if hasattr(result, 'keypoints') and result.keypoints is not None:
                keypoints = result.keypoints.xy[0]
                frame = draw_keypoints(frame, keypoints)

            cv2.putText(frame, f"Injury Risk: {injury_risk}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, f"Repetitions: {rep_count}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            processed_frames.append(frame)

    cap.release()
    
    return processed_frames

# Function to process live video stream
def process_live_video(exercise_type):
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("Error opening webcam")
        return

    stframe = st.empty()
    
    last_ibw_label = None
    rep_count = 0
    rep_started = False

    while True:
        ret, frame = cap.read()
        if not ret:
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

            # Draw keypoints on the frame if available
            if hasattr(result, 'keypoints') and result.keypoints is not None:
                keypoints = result.keypoints.xy[0]
                frame = draw_keypoints(frame, keypoints)

            cv2.putText(frame, f"Injury Risk: {injury_risk}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, f"Repetitions: {rep_count}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Update the Streamlit frame with the processed frame
            stframe.image(frame, channels="BGR")

    cap.release()

# Streamlit UI
st.title("Exercise Video Analysis")

exercise_type = st.selectbox("Select Exercise Type", list(yolo_models.keys()))

uploaded_file = st.file_uploader("Upload a Video", type=["mp4", "mov"])

if uploaded_file is not None:
    video_dir = './videos'
    if not os.path.exists(video_dir):
        os.makedirs(video_dir)

    video_path = os.path.join(video_dir, uploaded_file.name)

    
    
    # Save uploaded video
    with open(video_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.video(uploaded_file)

    if st.button("Process Video"):
        processed_frames = process_video_with_yolo(video_path, exercise_type)

        if processed_frames is not None:
            output_video_path = os.path.join('./processed_videos', f'processed_{uploaded_file.name}')
            out = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'XVID'), 30,
                                  (processed_frames[0].shape[1], processed_frames[0].shape[0]))

            for frame in processed_frames:
                out.write(frame)
            out.release()

            st.success(f"Video processed successfully! You can download it [here](./processed_videos/processed_{uploaded_file.name})")

if st.button("Start Live Stream"):
    process_live_video(exercise_type)

