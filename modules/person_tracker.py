"""
Person Tracker Module
Implements tracking of people across frames using position and size heuristics.
"""

import math
import time
import logging
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)

class TrackedPerson:
    """
    Represents a person being tracked across frames.
    """
    def __init__(self, detection, id):
        """
        Initialize a tracked person.
        
        Args:
            detection (dict): Person detection data
            id (int): Unique identifier for this person
        """
        self.id = id
        self.detection = detection
        self.bbox = self._get_bbox(detection)
        self.center = self._get_center(self.bbox)
        self.path = deque(maxlen=30)  # Track the last 30 positions
        self.path.append(self.center)
        self.crossed_line = False
        self.last_seen = time.time()
        self.confidence = detection.get('confidence', 0)
        self.age = 0  # Number of frames this person has been tracked
        self.missing_count = 0  # Number of consecutive frames person was not detected
    
    def update(self, detection):
        """
        Update the tracked person with a new detection.
        
        Args:
            detection (dict): Updated person detection data
        """
        self.detection = detection
        self.bbox = self._get_bbox(detection)
        self.center = self._get_center(self.bbox)
        self.path.append(self.center)
        self.last_seen = time.time()
        self.confidence = detection.get('confidence', 0)
        self.age += 1
        self.missing_count = 0
    
    def mark_missing(self):
        """Mark the person as missing in the current frame."""
        self.missing_count += 1
    
    def mark_crossed_line(self):
        """Mark the person as having crossed the counting line."""
        self.crossed_line = True
    
    def _get_bbox(self, detection):
        """
        Extract bounding box from detection.
        
        Args:
            detection (dict): Person detection data
            
        Returns:
            tuple: (left, top, right, bottom)
        """
        # Ensure we have the correct order (left < right, top < bottom)
        left = min(detection.get('left', 0), detection.get('right', 0))
        right = max(detection.get('left', 0), detection.get('right', 0))
        top = min(detection.get('top', 0), detection.get('bottom', 0))
        bottom = max(detection.get('top', 0), detection.get('bottom', 0))
        
        return (left, top, right, bottom)
    
    def _get_center(self, bbox):
        """
        Calculate the center point of the bounding box.
        
        Args:
            bbox (tuple): Bounding box (left, top, right, bottom)
            
        Returns:
            tuple: (x, y) center point
        """
        return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
    
    def get_width(self):
        """Get the width of the bounding box."""
        return abs(self.bbox[2] - self.bbox[0])
    
    def get_height(self):
        """Get the height of the bounding box."""
        return abs(self.bbox[3] - self.bbox[1])
    
    def get_area(self):
        """Get the area of the bounding box."""
        return self.get_width() * self.get_height()
    
    def is_active(self, max_missing_frames=5):
        """
        Check if the person is still active.
        
        Args:
            max_missing_frames (int): Maximum number of consecutive missing frames
            
        Returns:
            bool: True if active, False otherwise
        """
        return self.missing_count < max_missing_frames
    
    def to_dict(self):
        """
        Convert the tracked person to a dictionary.
        
        Returns:
            dict: Person data
        """
        return {
            'id': self.id,
            'bbox': self.bbox,
            'center': self.center,
            'path': list(self.path),
            'crossed_line': self.crossed_line,
            'confidence': self.confidence,
            'age': self.age,
            'missing_count': self.missing_count
        }


class PersonTracker:
    """
    Tracks people across frames and detects line crossings.
    """
    def __init__(self, line_x=320, confidence_threshold=0.5, max_match_distance=192):
        """
        Initialize the person tracker.
        
        Args:
            line_x (int): X-coordinate of the vertical counting line
            confidence_threshold (float): Minimum confidence for detections
            max_match_distance (float): Maximum distance for matching detections
        """
        self.next_id = 1
        self.tracked_people = []
        self.line_x = line_x
        self.confidence_threshold = confidence_threshold
        self.max_match_distance = max_match_distance
        # Frame dimensions for movement validation
        self.frame_width = 640
        self.frame_height = 480
    
    def update(self, detections):
        """
        Update tracking with new detections.
        
        Args:
            detections (list): List of person detections
            
        Returns:
            tuple: (list of tracked people, number of new line crossings)
        """
        # Filter detections by confidence
        detections = [d for d in detections if d.get('confidence', 0) >= self.confidence_threshold]
        
        if not self.tracked_people:
            # First frame, initialize tracked people
            for detection in detections:
                self.tracked_people.append(TrackedPerson(detection, self.next_id))
                self.next_id += 1
            return self.tracked_people, 0
        
        # Mark all tracked people as missing
        for person in self.tracked_people:
            person.mark_missing()
        
        # Match new detections to existing tracked people
        matched_indices = set()
        for detection in detections:
            best_match = None
            best_score = float('inf')
            best_idx = -1
            
            for idx, person in enumerate(self.tracked_people):
                if not person.is_active():
                    continue
                
                score = self._calculate_match_score(person, detection)
                if score < best_score:
                    best_score = score
                    best_match = person
                    best_idx = idx
            
            # If a good match is found, update the tracked person
            if best_match is not None and best_score < self.max_match_distance:
                best_match.update(detection)
                matched_indices.add(best_idx)
            else:
                # New person detected
                self.tracked_people.append(TrackedPerson(detection, self.next_id))
                self.next_id += 1
        
        # Check for line crossings
        crossing_count = self._detect_line_crossings()
        
        # Remove inactive tracked people
        self.tracked_people = [p for p in self.tracked_people if p.is_active()]
        
        return self.tracked_people, crossing_count
    
    def _calculate_match_score(self, person, detection):
        """
        Calculate a matching score between a tracked person and a detection.
        Lower score means better match.
        
        Args:
            person (TrackedPerson): Tracked person
            detection (dict): New detection
            
        Returns:
            float: Matching score
        """
        # Extract bounding box from detection
        new_bbox = (
            min(detection.get('left', 0), detection.get('right', 0)),
            min(detection.get('top', 0), detection.get('bottom', 0)),
            max(detection.get('left', 0), detection.get('right', 0)),
            max(detection.get('top', 0), detection.get('bottom', 0))
        )
        
        # Calculate center of new detection
        new_center = (
            (new_bbox[0] + new_bbox[2]) / 2,
            (new_bbox[1] + new_bbox[3]) / 2
        )
        
        # Distance between centers
        distance = math.sqrt(
            (person.center[0] - new_center[0]) ** 2 +
            (person.center[1] - new_center[1]) ** 2
        )
        
        # Calculate area of bounding boxes
        person_area = person.get_area()
        new_area = (new_bbox[2] - new_bbox[0]) * (new_bbox[3] - new_bbox[1])
        
        # Size ratio (higher is worse)
        if person_area > 0 and new_area > 0:
            size_ratio = max(person_area / new_area, new_area / person_area)
        else:
            size_ratio = float('inf')
        
        # Calculate speed (distance moved since last frame)
        # Higher speed means worse match
        speed_penalty = 0
        if len(person.path) >= 2:
            last_pos = person.path[-1]
            prev_pos = person.path[-2]
            expected_x = last_pos[0] + (last_pos[0] - prev_pos[0])
            expected_y = last_pos[1] + (last_pos[1] - prev_pos[1])
            
            prediction_error = math.sqrt(
                (expected_x - new_center[0]) ** 2 +
                (expected_y - new_center[1]) ** 2
            )
            
            # Check if movement is unreasonably fast (more than 25% of frame dimension)
            max_reasonable_movement = min(self.frame_width, self.frame_height) * 0.25
            if distance > max_reasonable_movement:
                speed_penalty = distance
        
        # Combine factors (weighted sum)
        score = distance + (size_ratio - 1) * 50 + speed_penalty
        
        return score
    
    def _detect_line_crossings(self):
        """
        Detect people crossing the counting line.
        
        Returns:
            int: Number of new line crossings
        """
        crossing_count = 0
        
        for person in self.tracked_people:
            if person.crossed_line:
                continue
            
            if len(person.path) < 2:
                continue
            
            # Check the last two positions
            current_pos = person.path[-1]
            previous_pos = person.path[-2]
            
            # Check if the person crossed the line from left to right
            if (previous_pos[0] < self.line_x and current_pos[0] >= self.line_x):
                person.mark_crossed_line()
                crossing_count += 1
                logger.info(f"Person {person.id} crossed the line!")
        
        return crossing_count