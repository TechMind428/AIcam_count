#!/usr/bin/env python3
"""
Simple test server to verify connectivity
"""

from flask import Flask, jsonify

# Initialize app
app = Flask(__name__)

@app.route('/')
def index():
    return "Test server is running!"

@app.route('/api/test')
def test_api():
    return jsonify({"status": "ok", "message": "API is working"})

if __name__ == '__main__':
    print("="*50)
    print("Starting test server at http://0.0.0.0:8080")
    print("Try accessing: http://localhost:8080/api/test")
    print("Press CTRL+C to quit")
    print("="*50)
    
    # Run server on port 8080
    app.run(host='0.0.0.0', port=8080, debug=True)