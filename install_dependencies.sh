#!/bin/bash
# Installation script for the People Counter application

# Terminate on any error
set -e

echo "Installing dependencies for People Counter application..."
echo "*******************************************************************************"
echo "***If you see error when install dependencies, try using venv and try again.***"
echo "*******************************************************************************"
echo ""


# Update package lists
sudo apt-get update

# Install system dependencies
sudo apt-get install -y \
    python3-pip \
    python3-opencv \
    python3-picamera2

# Create directory structure
mkdir -p modules static/css static/js templates

# Install Python dependencies
pip3 install flask flask-cors numpy watchdog

echo "Creating module directory structure..."
# The module directories should have been created when installing the application

echo "Installation complete!"
echo "To run the application, use: python3 app.py"
