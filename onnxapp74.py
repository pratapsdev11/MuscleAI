import os
import logging
from flask import Flask, render_template, send_from_directory, request, url_for, Response
import cv2
from moviepy.editor import VideoFileClip
from ultralytics import YOLO
from flask_cors import CORS, cross_origin

app = Flask(__name__)

CORS(app, supports_credentials=True)

# Configuration: Specify the directory where videos are stored
VIDEO_FOLDER = './videos'
PROCESSED_FOLDER = './processed_videos'
STATIC_FOLDER = './static'

app.config['VIDEO_FOLDER'] = VIDEO_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER

# Ensure directories exist
os.makedirs(app.config['VIDEO_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load the YOLO models
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
    elif exercise_type in ['sumo_deadlift', 'romanian_deadlift', 'zercher_squat', 'front_squat']:
        ibw_value = labels.get('up', 1.0)  # Use 'up' instead of 'ibw' for these exercises
        down_value = labels.get('down', 1.0)

    if ibw_value < 0.80 or down_value < 0.70:
        return "stop right now to prevent injury"
    else:
        return "No significant risk"

# Function to draw keypoints on the frame
def draw_keypoints(frame, keypoints):

    for point in keypoints:
        x, y = int(point[0]), int(point[1])
        cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)  # Draw keypoints as green circles
    return frame

# Function to process video with YOLO
def process_video_with_yolo(video_path, output_path, exercise_type):
    try:
        yolo_model = yolo_models[exercise_type]
        last_ibw_label = None
        rep_count = 0
        rep_started = False

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError("Error opening video file")

        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (frame_width, frame_height))

        results = yolo_model(source=video_path, stream=True, conf=0.3)

        for frame_idx, result in enumerate(results):
            frame = result.orig_img

            labels = {}
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls)
                    conf = float(box.conf)
                    label = result.names[class_id]
                    labels[label] = conf

            injury_risk = check_injury_risk(labels, exercise_type)

            if exercise_type in ['regular_deadlift', 'squat']:
                current_ibw_label = labels.get('ibw')
                current_down_label = labels.get('down')
            elif exercise_type in ['sumo_deadlift', 'romanian_deadlift', 'zercher_squat', 'front_squat']:
                current_ibw_label = labels.get('up')
                current_down_label = labels.get('down')

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
                keypoints = result.keypoints.xy[0]  # Get keypoints for the first detected person
                frame = draw_keypoints(frame, keypoints)

            cv2.putText(frame, f"Injury Risk: {injury_risk}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Repetitions: {rep_count}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            out.write(frame)

        cap.release()
        out.release()
    except Exception as e:
        logging.error(f"Error processing video: {e}")
        raise

# Global variables for live video processing
last_ibw_label = None
rep_count = 0
rep_started = False

# Function to process live video stream
def process_live_video(exercise_type):
    global last_ibw_label, rep_count, rep_started
    
    yolo_model = yolo_models[exercise_type]

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("Error opening webcam")

    def generate_frames():
        global last_ibw_label, rep_count, rep_started

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            results = yolo_model(source=frame, stream=True, conf=0.3)

            for result in results:
                frame = result.orig_img

                labels = {}
                if result.boxes is not None:
                    for box in result.boxes:
                        class_id = int(box.cls)
                        conf = float(box.conf)
                        label = result.names[class_id]
                        labels[label] = conf

                injury_risk = check_injury_risk(labels, exercise_type)

                if exercise_type in ['regular_deadlift', 'squat']:
                    current_ibw_label = labels.get('ibw')
                    current_down_label = labels.get('down')
                elif exercise_type in ['sumo_deadlift', 'romanian_deadlift', 'zercher_squat', 'front_squat']:
                    current_ibw_label = labels.get('up')
                    current_down_label = labels.get('down')

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
                    keypoints = result.keypoints.xy[0]  # Get keypoints for the first detected person
                    frame = draw_keypoints(frame, keypoints)

                cv2.putText(frame, f"Injury Risk: {injury_risk}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()

                # Yielding the frame with CORS headers
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Access-Control-Allow-Origin: http://localhost:3000\r\n'
                       b'Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n'
                       b'Access-Control-Allow-Headers: Content-Type\r\n\r\n' + frame + b'\r\n')

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/<filename>', methods=['GET'])
@cross_origin(origin='*')
def serve_video(filename):
    try:
        logging.debug(f"Serving video: {filename}")
        return send_from_directory(app.config['PROCESSED_FOLDER'], filename)
    except Exception as e:
        logging.error(f"Error serving video: {e}")
        return "Error serving video", 500

@app.route('/', methods=['GET', 'POST'])
@cross_origin(origin='*')
def index():
    if request.method == 'POST':
        if 'video' in request.files:
            file = request.files['video']
            if file.filename == '':
                return render_template('index.html', message='No selected file')

            exercise_type = request.form.get('exercise_type')  # Added a form field for selecting the exercise type

            video_path = os.path.join(app.config['VIDEO_FOLDER'], file.filename)
            file.save(video_path)

            try:
                processed_video_path = os.path.join(app.config['PROCESSED_FOLDER'], f'processed_{file.filename}')
                static_video_path = os.path.join(app.config['STATIC_FOLDER'], f'processed_{file.filename}')
                process_video_with_yolo(video_path, processed_video_path, exercise_type)

                clip = VideoFileClip(processed_video_path)
                clip.write_videofile(static_video_path, codec='libx264')

                video_url = url_for('serve_video', filename=f'processed_{file.filename}')
                return render_template('index.html', video_url=video_url)

            except Exception as e:
                logging.error(f"Error during processing: {e}")
                return render_template('index.html', message=f'Error during processing: {e}')
    
    return render_template('index.html')

@app.route('/live', methods=['POST', 'OPTIONS'])
@cross_origin(origin='*')
def live():
    # Handle preflight request
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response

    exercise_type = request.form.get('live_exercise_type')
    
    # Your live video processing logic goes here
    response = process_live_video(exercise_type)
    
    # Add CORS headers to the actual response
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    return response

if __name__ == '__main__':
    app.run(debug=True)

