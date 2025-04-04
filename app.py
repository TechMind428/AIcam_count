#!/usr/bin/env python3
"""
People Counter Web Application (Fixed version)
"""

import os
import logging
import traceback
import threading
from datetime import datetime
from threading import Thread, Lock, current_thread
from collections import deque

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from modules.file_monitor import FileMonitor
from modules.person_tracker import PersonTracker
from modules.line_counter import LineCounter

from pathlib import Path


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'people-counter-secret-key'

# Configuration
RESULTS_DIR = str(Path.home()) + '/temp'
LINE_X = 320  # Vertical line position
UPDATE_FREQUENCY = 200  # Default update frequency in milliseconds
MAX_DATA_POINTS = 50  # Number of data points to keep for the time-series graph
CONFIDENCE_THRESHOLD = 0.4  # Default confidence threshold
LOCK_TIMEOUT = 2.0  # Lock timeout in seconds

# Global state
current_frame = None
tracked_people = []
crossing_count = 0
crossing_history = deque(maxlen=MAX_DATA_POINTS)
time_labels = deque(maxlen=MAX_DATA_POINTS)
state_lock = Lock()
last_count_time = None
minute_counts = {}

# Custom timeout lock implementation
class TimeoutLock:
    def __init__(self, lock, timeout):
        self.lock = lock
        self.timeout = timeout
    
    def __enter__(self):
        if not self.lock.acquire(timeout=self.timeout):
            thread_name = current_thread().name
            logger.error(f"Thread {thread_name}: Lock acquisition timeout!")
            raise TimeoutError(f"Could not acquire lock within {self.timeout} seconds")
        return self.lock
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
        if exc_type is not None:
            logger.error(f"Exception in lock context: {exc_type.__name__}: {exc_val}")
            return False
        return True

def safe_lock():
    """Get a lock with timeout to prevent deadlocks"""
    return TimeoutLock(state_lock, LOCK_TIMEOUT)

def add_to_crossing_history():
    """Add the current count to the crossing history"""
    global last_count_time, crossing_history, time_labels
    
    thread_name = current_thread().name
    logger.info(f"Thread {thread_name}: Adding to crossing history")
    
    now = datetime.now()
    current_minute = now.strftime('%H:%M')
    
    try:
        # Initialize if this is first time seeing this minute
        if current_minute not in minute_counts:
            minute_counts[current_minute] = 0
        
        # Add new crossing to current minute's count
        minute_counts[current_minute] += 1
        
        with safe_lock():
            # Update history with latest minute counts
            if len(time_labels) == 0 or time_labels[-1] != current_minute:
                time_labels.append(current_minute)
                crossing_history.append(minute_counts[current_minute])
            else:
                # Update the last count if we're still in the same minute
                crossing_history[-1] = minute_counts[current_minute]
        
        logger.info(f"Thread {thread_name}: Successfully added to crossing history")
    except Exception as e:
        logger.error(f"Thread {thread_name}: Error in add_to_crossing_history: {e}")
        logger.error(traceback.format_exc())

def on_new_detection(detection_data):
    """
    Process new detection data
    
    Args:
        detection_data (dict): The detection data from the JSON file
    """
    global current_frame, tracked_people, crossing_count
    
    thread_name = current_thread().name
    logger.debug(f"Thread {thread_name}: Processing new detection data")
    
    try:
        # Extract person detections
        persons = [d for d in detection_data.get('detections', []) 
                if d.get('label') == 'person' and d.get('confidence', 0) >= CONFIDENCE_THRESHOLD]
        
        # Create a local copy to minimize lock time
        persons_copy = persons.copy() if persons else []
        
        # Update current frame data under lock
        with safe_lock():
            # Update current frame with detection data
            current_frame = {
                'time': detection_data.get('time'),
                'persons': persons_copy
            }
        
        # Process tracking outside of the lock
        new_tracked_people, new_crossings = person_tracker.update(persons_copy)
        
        # Update global state with minimal lock time
        with safe_lock():
            tracked_people = new_tracked_people
            if new_crossings > 0:
                crossing_count += new_crossings
                logger.info(f"Thread {thread_name}: New crossing detected! Total count: {crossing_count}")
        
        # Add to history outside of the main lock if needed
        if new_crossings > 0:
            add_to_crossing_history()
        
    except Exception as e:
        logger.error(f"Thread {thread_name}: Error in on_new_detection: {e}")
        logger.error(traceback.format_exc())

@app.route('/')
def index():
    """Render the main application page"""
    logger.info("Main page requested")
    return render_template('index.html', 
                           update_frequency=UPDATE_FREQUENCY,
                           confidence_threshold=CONFIDENCE_THRESHOLD)

@app.route('/api-test')
def api_test_page():
    """Render the API test page"""
    logger.info("API test page requested")
    return render_template('api_test.html')

@app.route('/api/test')
def test_api():
    """Simple test endpoint to verify API is working"""
    logger.info("Test API endpoint called")
    return jsonify({
        "status": "ok", 
        "message": "API is working", 
        "time": datetime.now().isoformat(),
        "thread": current_thread().name
    })

@app.route('/api/data')
def get_data():
    """API endpoint for getting current data"""
    thread_name = current_thread().name
    logger.info(f"Thread {thread_name}: Data API endpoint called")
    try:
        # Prepare data with minimal lock time
        with safe_lock():
            last_update = "No data" if current_frame is None else current_frame.get('time')
            tracks_copy = [p.to_dict() for p in tracked_people] if tracked_people else []
            count_copy = crossing_count
            labels_copy = list(time_labels)
            counts_copy = list(crossing_history)
            active_tracks = len(tracked_people)
        
        # Build response outside the lock
        data = {
            'timestamp': last_update,
            'detections': current_frame.get('persons', []) if current_frame else [],
            'tracks': tracks_copy,
            'crossing_count': count_copy,
            'history': {
                'labels': labels_copy,
                'counts': counts_copy
            },
            'line_x': LINE_X,
            'active_tracks': active_tracks
        }
        
        logger.info(f"Thread {thread_name}: Returning data with {active_tracks} tracks and count {count_copy}")
        return jsonify(data)
    except Exception as e:
        logger.error(f"Thread {thread_name}: Error in /api/data endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/api/reset', methods=['POST'])
def reset_count():
    """Reset the counting data"""
    global crossing_count, crossing_history, time_labels, minute_counts
    
    thread_name = current_thread().name
    logger.info(f"Thread {thread_name}: Reset count requested")
    
    try:
        with safe_lock():
            crossing_count = 0
            crossing_history.clear()
            time_labels.clear()
            minute_counts = {}
        
        logger.info(f"Thread {thread_name}: Count reset successful")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Thread {thread_name}: Error in reset_count: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update application settings"""
    global UPDATE_FREQUENCY, CONFIDENCE_THRESHOLD
    
    thread_name = current_thread().name
    logger.info(f"Thread {thread_name}: Update settings requested")
    
    try:
        data = request.json
        if 'update_frequency' in data:
            UPDATE_FREQUENCY = int(data['update_frequency'])
        
        if 'confidence_threshold' in data:
            CONFIDENCE_THRESHOLD = float(data['confidence_threshold'])
            person_tracker.confidence_threshold = CONFIDENCE_THRESHOLD
        
        logger.info(f"Thread {thread_name}: Settings updated successfully")
        return jsonify({
            'success': True,
            'update_frequency': UPDATE_FREQUENCY,
            'confidence_threshold': CONFIDENCE_THRESHOLD
        })
    except Exception as e:
        logger.error(f"Thread {thread_name}: Error in update_settings: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def get_status():
    """Get application status information"""
    thread_name = current_thread().name
    logger.info(f"Thread {thread_name}: Status requested")
    
    # Get all threads
    all_threads = threading.enumerate()
    thread_info = [{
        'name': t.name,
        'daemon': t.daemon,
        'alive': t.is_alive()
    } for t in all_threads]
    
    return jsonify({
        'status': 'ok',
        'time': datetime.now().isoformat(),
        'thread_count': len(all_threads),
        'threads': thread_info,
        'crossing_count': crossing_count,
        'has_data': current_frame is not None
    })

def start_background_tasks():
    """Start the background tasks for file monitoring"""
    # Initialize tracker and counter
    global person_tracker, line_counter
    person_tracker = PersonTracker(line_x=LINE_X, confidence_threshold=CONFIDENCE_THRESHOLD)
    line_counter = LineCounter(line_x=LINE_X)
    
    # Initialize and start file monitor
    file_monitor = FileMonitor(RESULTS_DIR, on_new_detection)
    file_monitor_thread = Thread(target=file_monitor.start_monitoring, name="FileMonitorThread")
    file_monitor_thread.daemon = True
    file_monitor_thread.start()
    
    logger.info(f"Monitoring directory: {RESULTS_DIR}")
    logger.info(f"Tracking line set at x={LINE_X}")

if __name__ == '__main__':
    try:
        # Ensure the results directory exists
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # Start background tasks
        start_background_tasks()
        
        # Print server information
        print("="*50)
        print(f"Starting People Counter server at http://0.0.0.0:8080")
        print(f"API test page available at: http://localhost:8080/api-test")
        print(f"Monitoring directory: {RESULTS_DIR}")
        print(f"Press CTRL+C to quit")
        print("="*50)
        
        # Start the web server with more explicit settings
        app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"ERROR STARTING SERVER: {e}")
        traceback.print_exc()