import os
import logging
import cv2
import numpy as np
from flask import Flask, render_template, send_from_directory, request, url_for, Response, jsonify
#from moviepy.editor import VideoFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from ultralytics import YOLO
from datetime import datetime

app = Flask(__name__)

# Configuration
app.config.update(
    VIDEO_FOLDER='./videos',
    PROCESSED_FOLDER='./processed_videos',
    STATIC_FOLDER='./static',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size
)

# Ensure directories exist
for folder in ['VIDEO_FOLDER', 'PROCESSED_FOLDER', 'STATIC_FOLDER']:
    os.makedirs(app.config[folder], exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load YOLO models
try:
    yolo_models = {
        'regular_deadlift': YOLO("models/best.pt"),
        'sumo_deadlift': YOLO("models/sumo_best.pt"),
        'squat': YOLO("models/squats_best.pt"),
        'romanian_deadlift': YOLO("models/best_romanian.pt"),
        "zercher_squat": YOLO("models/zercher_best.pt"),
        "front_squat": YOLO("models/front_squats_best.pt")
    }
except Exception as e:
    logger.error(f"Error loading YOLO models: {e}")
    raise
class MovementAnalyzer:
    def __init__(self, exercise_type):
        self.exercise_type = exercise_type
        self.form_scores = []  # ibw for regular/squat, up for others
        self.down_scores = []
        self.rep_count = 0
        
        # Rep counting parameters
        self.form_values = []  # Store recent form values for smoothing
        self.window_size = 5   # Number of frames to use for smoothing
        self.rep_threshold = 0.89  # Threshold for rep detection
        self.min_frames_between_reps = 10  # Minimum frames between reps to prevent double counting
        self.frames_since_last_rep = 0
        self.in_rep_motion = False
        self.rep_start_threshold = 0.85  # Start of rep threshold
        self.rep_end_threshold = 0.92    # End of rep threshold
        self.min_rep_frames = 5  # Minimum frames a rep motion should take
        self.current_rep_frames = 0

    def smooth_value(self, value):
        """Apply moving average smoothing to reduce noise"""
        self.form_values.append(value if value is not None else self.form_values[-1] if self.form_values else 0)
        if len(self.form_values) > self.window_size:
            self.form_values.pop(0)
        return sum(self.form_values) / len(self.form_values)

    def detect_rep(self, smoothed_value):
        """Detect repetition using state machine approach"""
        self.frames_since_last_rep += 1
        
        if smoothed_value is None:
            return
        
        # Update rep detection state
        if not self.in_rep_motion:
            # Looking for the start of a rep
            if (smoothed_value < self.rep_start_threshold and 
                self.frames_since_last_rep > self.min_frames_between_reps):
                self.in_rep_motion = True
                self.current_rep_frames = 1
        else:
            # In the middle of a rep motion
            self.current_rep_frames += 1
            
            # Check for rep completion
            if (smoothed_value > self.rep_end_threshold and 
                self.current_rep_frames >= self.min_rep_frames):
                self.rep_count += 1
                self.frames_since_last_rep = 0
                self.in_rep_motion = False
                self.current_rep_frames = 0
            
            # Reset if rep takes too long
            elif self.current_rep_frames > self.min_frames_between_reps * 2:
                self.in_rep_motion = False
                self.current_rep_frames = 0

    def process_frame(self, labels):
        """Process a single frame's labels and update metrics"""
        # Get appropriate form value based on exercise type
        if self.exercise_type in ['regular_deadlift', 'squat']:
            form_value = labels.get('ibw', None)
        else:
            form_value = labels.get('up', None)
        
        down_value = labels.get('down', None)

        # Update scores
        if form_value is not None:
            self.form_scores.append(form_value)
        if down_value is not None:
            self.down_scores.append(down_value)

        # Apply smoothing and detect reps
        smoothed_value = self.smooth_value(form_value)
        self.detect_rep(smoothed_value)
        
        return form_value, down_value

    def get_metrics(self):
        """Calculate and return movement metrics"""
        if not self.form_scores or not self.down_scores:
            return None

        metrics = {
            'frames_analyzed': len(self.form_scores),
            'repetitions': self.rep_count,
            'form_metrics': {
                'average': np.mean(self.form_scores),
                'min': min(self.form_scores),
                'max': max(self.form_scores),
                'consistency': 1 - (max(self.form_scores) - min(self.form_scores))
            },
            'depth_metrics': {
                'average': np.mean(self.down_scores),
                'min': min(self.down_scores),
                'max': max(self.down_scores),
                'consistency': 1 - (max(self.down_scores) - min(self.down_scores))
            }
        }

        # Calculate overall score out of 10
        form_component = metrics['form_metrics']['average'] * 0.6
        depth_component = metrics['depth_metrics']['average'] * 0.4
        overall_score = (form_component + depth_component) * 10

        metrics['movement_assessment'] = {
            'form_quality': self.get_quality_assessment(metrics['form_metrics']['average']),
            'depth_quality': self.get_quality_assessment(metrics['depth_metrics']['average']),
            'form_consistency': self.get_quality_assessment(metrics['form_metrics']['consistency']),
            'depth_consistency': self.get_quality_assessment(metrics['depth_metrics']['consistency']),
            'score': round(overall_score, 1)
        }

        return metrics

    @staticmethod
    def get_quality_assessment(value):
        """Return a qualitative assessment based on the metric value"""
        if value >= 0.9:
            return "Excellent"
        elif value >= 0.8:
            return "Very Good"
        elif value >= 0.7:
            return "Good"
        elif value >= 0.6:
            return "Fair"
        else:
            return "Needs Improvement"

def process_video(video_path, output_path, exercise_type):
    """Process video with YOLO and movement analysis"""
    try:
        analyzer = MovementAnalyzer(exercise_type)
        yolo_model = yolo_models[exercise_type]
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError("Error opening video file")

        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        out = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*'XVID'),
            fps,
            (frame_width, frame_height)
        )

        results = yolo_model(source=video_path, stream=True, conf=0.3)
        
        for result in results:
            frame = result.orig_img
            labels = {}
            
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls)
                    conf = float(box.conf)
                    label = result.names[class_id]
                    labels[label] = conf

            # Process frame and get metrics
            form_value, down_value = analyzer.process_frame(labels)
            
            # Draw keypoints if available
            if hasattr(result, 'keypoints') and result.keypoints is not None:
                keypoints = result.keypoints.xy[0]
                for point in keypoints:
                    x, y = int(point[0]), int(point[1])
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

            # Add overlay information
            metrics = analyzer.get_metrics()
            if metrics:
                cv2.putText(frame, f"Score: {metrics['movement_assessment']['score']}/10",
                          (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Reps: {metrics['repetitions']}",
                          (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            out.write(frame)

        cap.release()
        out.release()
        
        return analyzer.get_metrics()

    except Exception as e:
        logger.error(f"Error processing video: {e}")
        raise

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'video' not in request.files:
            return render_template('index.html', message='No video file uploaded')
        
        file = request.files['video']
        if file.filename == '':
            return render_template('index.html', message='No selected file')

        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov')):
            return render_template('index.html', message='Invalid file type. Please upload MP4, AVI, or MOV files')

        exercise_type = request.form.get('exercise_type')
        if exercise_type not in yolo_models:
            return render_template('index.html', message='Invalid exercise type')

        try:
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{file.filename}"
            video_path = os.path.join(app.config['VIDEO_FOLDER'], filename)
            processed_path = os.path.join(app.config['PROCESSED_FOLDER'], f'processed_{filename}')
            
            file.save(video_path)
            
            # Process video and get metrics
            metrics = process_video(video_path, processed_path, exercise_type)
            
            # Convert processed video to MP4 for web compatibility
            clip = VideoFileClip(processed_path)
            web_path = os.path.join(app.config['STATIC_FOLDER'], f'web_{filename}.mp4')
            clip.write_videofile(web_path, codec='libx264')
            
            video_url = url_for('static', filename=f'web_{filename}.mp4')
            
            return render_template('index.html',
                                video_url=video_url,
                                movement_analysis={'score': f"{metrics['movement_assessment']['score']}/10",
                                                'metrics': metrics})

        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            return render_template('index.html', message=f'Error processing video: {str(e)}')

    return render_template('index.html')

@app.route('/live', methods=['POST'])
def live():
    exercise_type = request.form.get('live_exercise_type')
    if exercise_type not in yolo_models:
        return "Invalid exercise type", 400

    def generate_frames():
        cap = cv2.VideoCapture(0)
        analyzer = MovementAnalyzer(exercise_type)
        
        try:
            while True:
                success, frame = cap.read()
                if not success:
                    break

                results = yolo_models[exercise_type](source=frame, stream=True, conf=0.3)
                
                for result in results:
                    frame = result.orig_img
                    labels = {}
                    
                    if result.boxes is not None:
                        for box in result.boxes:
                            class_id = int(box.cls)
                            conf = float(box.conf)
                            label = result.names[class_id]
                            labels[label] = conf

                    form_value, down_value = analyzer.process_frame(labels)
                    
                    if hasattr(result, 'keypoints') and result.keypoints is not None:
                        keypoints = result.keypoints.xy[0]
                        for point in keypoints:
                            x, y = int(point[0]), int(point[1])
                            cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

                    metrics = analyzer.get_metrics()
                    if metrics:
                        cv2.putText(frame, f"Score: {metrics['movement_assessment']['score']}/10",
                                  (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        cv2.putText(frame, f"Reps: {metrics['repetitions']}",
                                  (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        finally:
            cap.release()

    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)
