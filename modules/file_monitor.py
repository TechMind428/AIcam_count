"""
File Monitor Module
Monitors a directory for new JSON files containing detection results
and processes them as they appear.
"""

import os
import json
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class DetectionFileHandler(FileSystemEventHandler):
    """
    Handler for detection JSON file events.
    Processes new files as they are created.
    """
    def __init__(self, callback):
        """
        Initialize the handler.
        
        Args:
            callback (function): Function to call with the detection data
        """
        self.callback = callback
        self.processed_files = set()
        self.last_processed_time = ""
    
    def on_created(self, event):
        """
        Handle file creation events.
        
        Args:
            event: File system event
        """
        if not event.is_directory and event.src_path.endswith('.json'):
            self._process_file(event.src_path)
    
    def on_modified(self, event):
        """
        Handle file modification events.
        
        Args:
            event: File system event
        """
        if not event.is_directory and event.src_path.endswith('.json'):
            self._process_file(event.src_path)
    
    def _process_file(self, file_path):
        """
        Process a detection JSON file.
        
        Args:
            file_path (str): Path to the JSON file
        """
        # Skip if already processed
        if file_path in self.processed_files:
            return
        
        try:
            # Check if file exists and has content
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return
                
            # Read the file content first
            with open(file_path, 'r') as f:
                content = f.read().strip()
            
            # Check if content is valid
            if not content:
                return
                
            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                return
            
            # Extract timestamp from data
            timestamp = data.get('time', '')
            
            # Process only if newer than the last processed file
            if timestamp > self.last_processed_time:
                self.last_processed_time = timestamp
                logger.info(f"Processing file: {os.path.basename(file_path)}")
                
                # Call the callback with the detection data
                self.callback(data)
            
            # Mark as processed
            self.processed_files.add(file_path)
            
            # Limit size of processed files set
            if len(self.processed_files) > 1000:
                self.processed_files = set(sorted(self.processed_files)[-500:])
        
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")


class FileMonitor:
    """
    Monitors a directory for new detection JSON files.
    """
    def __init__(self, directory, callback):
        """
        Initialize the file monitor.
        
        Args:
            directory (str): Directory to monitor
            callback (function): Function to call with detection data
        """
        self.directory = directory
        self.callback = callback
        self.event_handler = DetectionFileHandler(callback)
        self.observer = Observer()
    
    def start_monitoring(self):
        """Start monitoring the directory for new files."""
        logger.info(f"Starting to monitor directory: {self.directory}")
        
        # Set up the observer
        self.observer.schedule(self.event_handler, self.directory, recursive=False)
        self.observer.start()
        
        try:
            # Keep the thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        
        self.observer.join()
    
    def stop_monitoring(self):
        """Stop monitoring the directory."""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()