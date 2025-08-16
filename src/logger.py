#zone_intrusion_detector\src\logger.py
import logging
import os
from datetime import datetime

class EventLogger:
    def __init__(self, log_file="logs/intrusion_events.log"):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        # Create a unique logger name
        self.logger = logging.getLogger("IntrusionEventLogger")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # Prevent duplicate logs
        
        # Clear existing handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(message)s", 
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh.setFormatter(formatter)
        
        self.logger.addHandler(fh)
    
    def log_event(self, event_type, obj_id, zone, location=None):
        message = f"{event_type} - Object {obj_id} in zone '{zone}'"
        if location:
            message += f" at ({location[0]}, {location[1]})"
        self.logger.info(message)