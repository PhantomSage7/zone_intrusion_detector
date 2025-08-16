#zone_intrusion_detector\src\zone_manager.py
import json
import os
from shapely.geometry import Point, Polygon

class ZoneManager:
    def __init__(self):
        self.zones = []  # Format: [{"label": str, "points": list, "color": str, "polygon": shapely.Polygon}]
        
    def add_zone(self, label, points, color):
        polygon = Polygon(points)
        self.zones.append({
            "label": label,
            "points": points,
            "color": color,
            "polygon": polygon
        })
    
    def point_in_zones(self, point):
        """Return set of zone labels containing the point"""
        p = Point(point)
        containing_zones = set()
        for zone in self.zones:
            if zone["polygon"].contains(p):
                containing_zones.add(zone["label"])
        return containing_zones
    
    def save_zones(self, file_path):
        # Convert to serializable format
        serializable_zones = []
        for zone in self.zones:
            serializable_zones.append({
                "label": zone["label"],
                "points": zone["points"],
                "color": zone["color"]
            })
        
        with open(file_path, "w") as f:
            json.dump(serializable_zones, f, indent=2)
    
    def load_zones(self, file_path):
        if not os.path.exists(file_path):
            return
        
        with open(file_path, "r") as f:
            serializable_zones = json.load(f)
        
        self.zones = []
        for zone in serializable_zones:
            polygon = Polygon(zone["points"])
            self.zones.append({
                "label": zone["label"],
                "points": zone["points"],
                "color": zone["color"],
                "polygon": polygon
            })
    
    def clear_zones(self):
        self.zones = []