# People Counter Web Application

A local web application for Raspberry Pi 5 with AI Camera (IMX500) that counts people crossing a line and visualizes the results.

[日本語版 README](README_ja.md)

## Features

- Real-time visualization of people detection with bounding boxes
- Person tracking across frames using advanced heuristics
- Line-crossing detection and counting
- Time-series graph of people counts
- Adjustable settings (thresholds, update frequency, etc.)
- Robust tracking that can handle detection gaps

## Prerequisites

- Raspberry Pi 4/5 (We didn't test with other model)
- Raspberry Pi AI Camera (IMX500)
- Object detection model for people detection deployed to the IMX500
- Python 3.9+
- IMX500 AI Camera setup completed per [official documentation](https://www.raspberrypi.com/documentation/accessories/ai-camera.html))
  - This includes installing required packages with `sudo apt install imx-500-all` and verifying that demo applications work properly

## Installation

1. Clone this repository to your Raspberry Pi:

```bash
git clone https://github.com/TechMind428/AIcam_count.git
cd AIcam_count
```

2. Run the installation script:

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh

# You may need to use a virtual environment to complete installation
e.g.)
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
```

## Directory Structure

```
AIcam_count/
├── app.py                 # Main application entry point
├── output_meta.py         # Application to save camera metadata to files
├── modules/
│   ├── file_monitor.py    # JSON file monitoring
│   ├── person_tracker.py  # Person tracking algorithm
│   └── line_counter.py    # Line crossing detection
├── static/
│   ├── css/
│   │   └── style.css      # Application styling
│   └── js/
│       └── main.js        # Frontend functionality
└── templates/
    └── index.html         # Main application page
```

## Usage

1. Make sure you have a separate process running that deploys the object detection model to the IMX500 camera and outputs JSON files to `/home/temp`.

2. Start the web application:

```bash
source .venv/bin/activate # if you use venv | change venv directory to your environment
python output_meta.py # You may need to open another terminal
python app.py
```

3. Open a web browser and navigate to:
   - `http://localhost:8080` (if accessing from the Raspberry Pi)
   - `http://{raspberry-pi-ip}:8080` (if accessing from another device on the same network)

## Configuration

You can adjust these settings in the web interface:

- **Update Frequency**: How often the UI refreshes (in milliseconds)
- **Confidence Threshold**: Minimum confidence score for a detection to be considered valid
- **Reset Count**: Button to reset the people counter

## Technical Implementation Details

### Person Tracking

The application tracks people across frames using:

- Distance between centers of bounding boxes
- IoU (Intersection over Union) of bounding boxes
- Size similarity of bounding boxes
- Movement trajectory and speed estimation

This approach helps maintain person identity even with occasional detection gaps.

### Line Crossing Detection

A vertical line is positioned at x=320 (the center of the 640x480 frame). The application:

- Tracks when a person's center crosses from left to right
- Ensures one-way counting (ignores U-turns)
- Counts only when confidence is above threshold

### JSON File Monitoring

The application watches for new JSON files in the specified directory and processes them as they appear. The expected JSON format is:

```json
{
    "time": "20250303145302409",
    "detections": [
        {
            "label": "person",
            "confidence": 0.77734375,
            "left": 625.0,
            "top": 0.0,
            "right": 44.0,
            "bottom": 470.0
        },
        ...
    ]
}
```

## License

[MIT License](LICENSE)
