#!/usr/bin/env python3
"""
Simplified People Counter Web Application
A minimal version for debugging purposes
"""

import os
import logging
from datetime import datetime
from threading import Lock

from flask import Flask, render_template, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'people-counter-secret-key'

# Global state
state_lock = Lock()
crossing_count = 0

@app.route('/')
def index():
    """Render the main application page"""
    logger.info("Main page requested")
    return render_template('index.html')

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
        "time": datetime.now().isoformat()
    })

@app.route('/api/data')
def get_data():
    """API endpoint for getting current data"""
    logger.info("Data API endpoint called")
    try:
        data = {
            'timestamp': datetime.now().isoformat(),
            'detections': [],
            'tracks': [],
            'crossing_count': crossing_count,
            'history': {
                'labels': ["12:00", "12:01", "12:02"],
                'counts': [1, 2, 3]
            },
            'line_x': 320,
            'active_tracks': 0
        }
        
        logger.info("Returning dummy data")
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error in /api/data endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_count():
    """Reset the counting data"""
    global crossing_count
    
    with state_lock:
        crossing_count = 0
    
    return jsonify({'success': True})

if __name__ == '__main__':
    try:
        # Print server information
        print("="*50)
        print(f"Starting Simplified People Counter server at http://0.0.0.0:8080")
        print(f"API test page available at: http://localhost:8080/api-test")
        print(f"Press CTRL+C to quit")
        print("="*50)
        
        # Start the web server
        app.run(host='0.0.0.0', port=8080, debug=True)
    except Exception as e:
        print(f"ERROR STARTING SERVER: {e}")
        import traceback
        traceback.print_exc()