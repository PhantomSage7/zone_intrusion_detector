#zone_intrusion_detector\src\detection_engine.py
import os
import cv2
import time
import logging
import torch
import numpy as np
from ultralytics import YOLO
from src.tracker import CentroidTracker
from src.zone_manager import ZoneManager
from src.logger import EventLogger

torch.set_float32_matmul_precision('high')

class DetectionEngine:
    def __init__(self, video_path, zone_manager, event_logger, config):
        self.zone_manager = zone_manager
        self.event_logger = event_logger
        self.config = config
        self.app_logger = logging.getLogger(__name__)
        self.gui_callback = lambda text: None
        self.object_zone_states = {}
        
        try:
            model_path = config["model"]
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            self.model = YOLO(model_path, task='detect')
            self.app_logger.info(f"Loaded YOLO model: {model_path}")
        except Exception as e:
            self.app_logger.error(f"Error loading model: {str(e)}")
            raise RuntimeError(f"Model initialization failed: {str(e)}")
        
        self.tracker = CentroidTracker(
            max_disappeared=config["max_disappeared"],
            max_distance=config["max_distance"]
        )
        
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")
        
        self.frame_count = 0
        self.prev_objects = {}
        self.start_time = time.time()
        
    def process_frame(self, frame):
        results = self.model(frame, 
                             classes=self.config["classes"], 
                             conf=self.config["confidence"],
                             verbose=False)
        
        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                detections.append((x1, y1, x2, y2, cls_id, conf))
        
        objects = self.tracker.update(detections)
        self.process_intrusions(objects)
        frame = self.visualize(frame, objects)
        
        self.frame_count += 1
        self.prev_objects = objects
        return frame
    
    def process_intrusions(self, current_objects):
        # Initialize new objects
        for obj_id in current_objects:
            if obj_id not in self.object_zone_states:
                self.object_zone_states[obj_id] = {}
        
        # Process each object
        for obj_id, obj in current_objects.items():
            centroid = (obj["centroid_x"], obj["centroid_y"])
            current_zones = self.zone_manager.point_in_zones(centroid)
            
            # Get previous zones
            prev_zones = set()
            if obj_id in self.prev_objects:
                prev_zones = self.prev_objects[obj_id]["zones"]
            
            # Check for new entries
            for zone in current_zones:
                if zone not in self.object_zone_states[obj_id]:
                    self.object_zone_states[obj_id][zone] = {
                        "in_zone": False,
                        "entry_time": time.time()
                    }
                
                # Only trigger entry if not already in zone
                if not self.object_zone_states[obj_id][zone]["in_zone"]:
                    # Require 100ms in zone to confirm entry
                    if time.time() - self.object_zone_states[obj_id][zone]["entry_time"] > 0.1:
                        self.event_logger.log_event("ENTRY", obj_id, zone, centroid)
                        self.gui_callback(f"ENTRY - Object {obj_id} entered {zone}")
                        self.object_zone_states[obj_id][zone]["in_zone"] = True
            
            # Check for exits
            for zone in prev_zones - current_zones:
                if zone in self.object_zone_states[obj_id]:
                    if self.object_zone_states[obj_id][zone]["in_zone"]:
                        self.event_logger.log_event("EXIT", obj_id, zone, centroid)
                        self.gui_callback(f"EXIT - Object {obj_id} exited {zone}")
                        self.object_zone_states[obj_id][zone]["in_zone"] = False
                        # Reset entry time for potential re-entry
                        self.object_zone_states[obj_id][zone]["entry_time"] = time.time()
            
            # Update object state
            obj["zones"] = current_zones

    def set_gui_callback(self, callback):
        self.gui_callback = callback
 
    def visualize(self, frame, objects):
        for zone in self.zone_manager.zones:
            points = np.array(zone["points"], np.int32)
            points = points.reshape((-1, 1, 2))
            color = tuple(int(zone["color"][i:i+2], 16) for i in (1, 3, 5))
            cv2.polylines(frame, [points], True, color, 2)
            cv2.putText(frame, zone["label"], points[0][0], 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        for obj_id, obj in objects.items():
            x1, y1, x2, y2 = obj["bbox"]
            cx, cy = obj["centroid_x"], obj["centroid_y"]
            
            # Draw moving centroid (should update each frame)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)
            
            label = f"ID:{obj_id} {self.model.names[obj['class_id']]}"
            cv2.putText(frame, label, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            if obj["zones"]:
                zones_str = ",".join(obj["zones"])
                cv2.putText(frame, zones_str, (x1, y2 + 20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        fps = self.frame_count / (time.time() - self.start_time)
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return frame
    
    def cleanup(self):
        if self.cap:
            self.cap.release()