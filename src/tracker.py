#zone_intrusion_detector\src\tracker.py
import numpy as np
from scipy.spatial import distance
import collections

class CentroidTracker:
    def __init__(self, max_disappeared=30, max_distance=70):
        self.next_id = 0
        self.objects = {}
        self.disappeared = {}
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.centroid_history = {}
        
    def update(self, detections):
        current_objects = {}
        
        if len(detections) == 0:
            for obj_id in list(self.disappeared.keys()):
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)
            return current_objects
        
        centroids = np.zeros((len(detections), 2), dtype="int")
        
        for (i, (x1, y1, x2, y2, cls_id, conf)) in enumerate(detections):
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            centroids[i] = (cx, cy)
        
        if len(self.objects) == 0:
            for i in range(len(centroids)):
                self.register(centroids[i], detections[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = [obj["centroid"] for obj in self.objects.values()]
            
            dist_matrix = distance.cdist(np.array(object_centroids), centroids)
            rows = dist_matrix.min(axis=1).argsort()
            cols = dist_matrix.argmin(axis=1)[rows]
            
            used_rows = set()
            used_cols = set()
            
            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if dist_matrix[row, col] > self.max_distance:
                    continue
                    
                obj_id = object_ids[row]
                
                # Update centroid position
                new_centroid = centroids[col]
                if obj_id in self.centroid_history:
                    self.centroid_history[obj_id].append(new_centroid)
                    if len(self.centroid_history[obj_id]) > 5:
                        self.centroid_history[obj_id].popleft()
                    # Calculate smoothed centroid
                    hist = list(self.centroid_history[obj_id])
                    avg_x = sum(p[0] for p in hist) // len(hist)
                    avg_y = sum(p[1] for p in hist) // len(hist)
                    smoothed_centroid = (avg_x, avg_y)
                else:
                    smoothed_centroid = new_centroid
                    self.centroid_history[obj_id] = collections.deque([new_centroid], maxlen=5)
                
                # Update object properties
                self.objects[obj_id]["centroid"] = smoothed_centroid
                self.objects[obj_id]["centroid_x"] = smoothed_centroid[0]  # FIX: Update centroid_x
                self.objects[obj_id]["centroid_y"] = smoothed_centroid[1]  # FIX: Update centroid_y
                self.objects[obj_id]["bbox"] = detections[col][:4]
                self.objects[obj_id]["class_id"] = detections[col][4]
                self.disappeared[obj_id] = 0
                current_objects[obj_id] = self.objects[obj_id]
                
                used_rows.add(row)
                used_cols.add(col)
            
            unused_rows = set(range(dist_matrix.shape[0])).difference(used_rows)
            unused_cols = set(range(dist_matrix.shape[1])).difference(used_cols)
            
            for row in unused_rows:
                obj_id = object_ids[row]
                self.disappeared[obj_id] += 1
                if self.disappeared[obj_id] > self.max_disappeared:
                    self.deregister(obj_id)
                else:
                    current_objects[obj_id] = self.objects[obj_id]
            
            for col in unused_cols:
                self.register(centroids[col], detections[col])
        
        return current_objects
    
    def register(self, centroid, detection):
        self.objects[self.next_id] = {
            "centroid": centroid,
            "centroid_x": centroid[0],  # Initialize centroid_x
            "centroid_y": centroid[1],  # Initialize centroid_y
            "bbox": detection[:4],
            "class_id": detection[4],
            "confidence": detection[5],
            "zones": set()
        }
        self.disappeared[self.next_id] = 0
        self.centroid_history[self.next_id] = collections.deque([centroid], maxlen=5)
        self.next_id += 1
    
    def deregister(self, obj_id):
        if obj_id in self.objects:
            del self.objects[obj_id]
        if obj_id in self.disappeared:
            del self.disappeared[obj_id]
        if obj_id in self.centroid_history:
            del self.centroid_history[obj_id]