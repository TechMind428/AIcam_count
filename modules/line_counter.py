"""
Line Counter Module
Handles detection of line crossings by tracked people.
"""

import logging

logger = logging.getLogger(__name__)

class LineCounter:
    """
    Counts people crossing a specified line.
    """
    def __init__(self, line_x=320):
        """
        Initialize the line counter.
        
        Args:
            line_x (int): X-coordinate of the vertical counting line
        """
        self.line_x = line_x
        self.total_count = 0
        self.crossed_ids = set()  # IDs of people who have already crossed the line
    
    def check_crossing(self, person, previous_center=None):
        """
        Check if a person has crossed the line.
        
        Args:
            person: TrackedPerson object
            previous_center: Previous center position (x, y)
            
        Returns:
            bool: True if the person crossed the line, False otherwise
        """
        # Skip if already counted
        if person.id in self.crossed_ids:
            return False
        
        # Get current center
        current_center = person.center
        
        # If no previous center, use the first point in the path
        if previous_center is None and len(person.path) > 1:
            previous_center = person.path[-2]
        
        # Can't determine crossing without previous position
        if previous_center is None:
            return False
        
        # Check if crossed line from left to right
        if (previous_center[0] < self.line_x and current_center[0] >= self.line_x):
            self.crossed_ids.add(person.id)
            self.total_count += 1
            logger.info(f"Person {person.id} crossed the line! Total count: {self.total_count}")
            return True
        
        return False
    
    def reset(self):
        """Reset the counter."""
        self.total_count = 0
        self.crossed_ids.clear()
    
    def get_count(self):
        """Get the current total count."""
        return self.total_count