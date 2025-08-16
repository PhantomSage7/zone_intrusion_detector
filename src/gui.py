#zone_intrusion_detector\src\gui.py
import os
import json
import cv2
import numpy as np
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush, QPolygon, QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QFileDialog, QMessageBox, QInputDialog, QGroupBox, QStatusBar
)
from src.detection_engine import DetectionEngine
from src.zone_manager import ZoneManager
from src.logger import EventLogger

class VideoWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.current_frame = None
        self.scale_factor = 1.0

    def set_frame(self, frame):
        if frame is not None:
            self.current_frame = frame
            self.display_frame()

    def display_frame(self):
        if self.current_frame is not None:
            h, w, ch = self.current_frame.shape
            bytes_per_line = ch * w
            q_img = QImage(self.current_frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
            self.setPixmap(QPixmap.fromImage(q_img).scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            self.scale_factor = min(
                self.width() / w,
                self.height() / h
            )

    def resizeEvent(self, event):
        self.display_frame()

    def map_to_frame(self, point):
        if self.pixmap():
            pixmap_size = self.pixmap().size()
            label_size = self.size()
            x_offset = (label_size.width() - pixmap_size.width()) // 2
            y_offset = (label_size.height() - pixmap_size.height()) // 2
            return QPoint(
                int((point.x() - x_offset) / self.scale_factor),
                int((point.y() - y_offset) / self.scale_factor)
            )
        return point

class MainWindow(QMainWindow):
    def __init__(self, settings, zone_colors, event_logger, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.zone_colors = zone_colors
        self.zone_manager = ZoneManager()
        self.event_logger = event_logger  # Store event logger
        self.init_ui()
        self.init_state()
        self.test_video_loaded = False
        

    def init_ui(self):
        # Main window setup
        self.setWindowTitle(self.settings["app"]["title"])
        self.setGeometry(100, 100, *self.settings["app"]["geometry"])
        self.setStyleSheet(self.settings["app"]["stylesheet"])

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel - Video display
        left_panel = QVBoxLayout()
        self.video_widget = VideoWidget()
        left_panel.addWidget(self.video_widget)

        # Right panel - Controls
        right_panel = QVBoxLayout()
        right_panel.setAlignment(Qt.AlignTop)

        # Zone management group
        zone_group = QGroupBox("Zone Management")
        zone_layout = QVBoxLayout()
        
        self.zone_list = QListWidget()
        self.zone_list.setMinimumHeight(150)
        zone_layout.addWidget(self.zone_list)
        
        btn_layout = QHBoxLayout()
        self.btn_draw = QPushButton("Draw Zone")
        self.btn_draw.clicked.connect(self.start_drawing)
        self.btn_save = QPushButton("Save Zones")
        self.btn_save.clicked.connect(self.save_zones)
        self.btn_load = QPushButton("Load Zones")
        self.btn_load.clicked.connect(self.load_zones)
        self.btn_clear = QPushButton("Clear All")
        self.btn_clear.clicked.connect(self.clear_zones)
        
        btn_layout.addWidget(self.btn_draw)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_clear)
        zone_layout.addLayout(btn_layout)
        
        zone_group.setLayout(zone_layout)
        right_panel.addWidget(zone_group)

        # Video control group
        video_group = QGroupBox("Video Control")
        video_layout = QVBoxLayout()
        
        self.btn_open = QPushButton("Open Video")
        self.btn_open.clicked.connect(self.open_video)
        self.btn_play = QPushButton("Play/Pause")
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_detect = QPushButton("Start Detection")
        self.btn_detect.setEnabled(False)
        self.btn_detect.clicked.connect(self.toggle_detection)
        
        video_layout.addWidget(self.btn_open)
        video_layout.addWidget(self.btn_play)
        video_layout.addWidget(self.btn_detect)
        video_group.setLayout(video_layout)
        right_panel.addWidget(video_group)

        # Event log group
        log_group = QGroupBox("Event Log")
        log_layout = QVBoxLayout()
        
        self.event_list = QListWidget()
        self.event_list.setMinimumHeight(200)
        log_layout.addWidget(self.event_list)
        
        log_group.setLayout(log_layout)
        right_panel.addWidget(log_group)

        # Add panels to main layout
        main_layout.addLayout(left_panel, 70)
        main_layout.addLayout(right_panel, 30)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Video timer
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self.next_frame)

    def init_state(self):
        self.video_path = None
        self.cap = None
        self.current_frame = None
        self.playing = False
        self.detecting = False
        self.drawing = False
        self.current_polygon = []
        self.detection_engine = None
        self.update_zone_list()
        from src.model_utils import download_test_video
        download_test_video()

    def open_video(self):
        if not self.test_video_loaded:
            from src.model_utils import download_test_video
            path = download_test_video()
            self.test_video_loaded = True
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open Video", "", "Video Files (*.mp4 *.avi *.mov)"
            )

        if path:
            self.video_path = path
            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                self.status_bar.showMessage("Error opening video file")
                return
            
            self.status_bar.showMessage(f"Loaded: {os.path.basename(path)}")
            self.btn_play.setEnabled(True)
            self.btn_detect.setEnabled(True)
            self.play_video()

    def play_video(self):
        if not self.playing:
            self.video_timer.start(30)  # ~33 FPS
            self.btn_play.setText("Pause")
            self.playing = True
        else:
            self.video_timer.stop()
            self.btn_play.setText("Play")
            self.playing = False

    def toggle_playback(self):
        if self.cap and self.cap.isOpened():
            self.play_video()

    def toggle_detection(self):
        if not self.detecting:
            if not self.zone_manager.zones:
                QMessageBox.warning(self, "No Zones", "Please define at least one zone first")
                return
            
            self.detection_engine = DetectionEngine(
                self.video_path,
                self.zone_manager,
                self.event_logger,  # Pass the event logger
                self.settings["detection"]
            )

            self.detecting = True
            self.btn_detect.setText("Stop Detection")
            self.btn_draw.setEnabled(False)
            self.status_bar.showMessage("Detection running...")
            self.detection_engine.set_gui_callback(self.add_event_to_list)
        else:
            self.detecting = False
            self.detection_engine = None
            self.btn_detect.setText("Start Detection")
            self.btn_draw.setEnabled(True)
            self.status_bar.showMessage("Detection stopped")


    def add_event_to_list(self, event_text):
        self.event_list.addItem(event_text)
        self.event_list.scrollToBottom()

    # In the next_frame method:
    def next_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                if self.detecting and self.detection_engine:
                    try:
                        frame = self.detection_engine.process_frame(frame)
                    except Exception as e:
                        self.status_bar.showMessage(f"Detection error: {str(e)}")
                        self.app_logger.error(f"Detection error: {str(e)}")
                
                self.current_frame = frame
                self.video_widget.set_frame(frame)
            else:
                self.video_timer.stop()
                self.playing = False
                self.btn_play.setText("Play")
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    def start_drawing(self):
        if not self.playing:
            self.drawing = True
            self.status_bar.showMessage("Drawing mode - Click to add points, Right-click to finish")
        else:
            QMessageBox.warning(self, "Video Playing", "Pause video before drawing zones")

    def finish_drawing(self):
        if len(self.current_polygon) >= 3:
            label, ok = QInputDialog.getText(
                self, "Zone Label", "Enter zone label:"
            )
            if ok and label:
                color_idx = len(self.zone_manager.zones) % len(self.zone_colors)
                color = self.zone_colors[color_idx]
                self.zone_manager.add_zone(label, self.current_polygon, color)
                self.update_zone_list()
            self.current_polygon = []
        self.drawing = False
        self.status_bar.showMessage("Ready")

    def mousePressEvent(self, event):
        if self.drawing and event.button() == Qt.LeftButton:
            frame_point = self.video_widget.map_to_frame(event.pos())
            self.current_polygon.append((frame_point.x(), frame_point.y()))
            self.draw_current_polygon()
        elif self.drawing and event.button() == Qt.RightButton:
            self.finish_drawing()

    def draw_current_polygon(self):
        if self.current_frame is None or not self.current_polygon:
            return
        
        frame = self.current_frame.copy()
        pts = np.array(self.current_polygon, np.int32)
        pts = pts.reshape((-1, 1, 2))
        
        # Draw polygon
        cv2.polylines(frame, [pts], True, (0, 255, 255), 2)
        
        # Draw vertices
        for point in self.current_polygon:
            cv2.circle(frame, point, 5, (0, 0, 255), -1)
        
        self.video_widget.set_frame(frame)

    def update_zone_list(self):
        self.zone_list.clear()
        for zone in self.zone_manager.zones:
            item = f"{zone['label']} ({len(zone['points'])} points)"
            self.zone_list.addItem(item)

    def save_zones(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Zones", "", "JSON Files (*.json)"
        )
        if path:
            self.zone_manager.save_zones(path)
            self.status_bar.showMessage(f"Zones saved to {os.path.basename(path)}")

    def load_zones(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Zones", "", "JSON Files (*.json)"
        )
        if path:
            self.zone_manager.load_zones(path)
            self.update_zone_list()
            self.status_bar.showMessage(f"Zones loaded from {os.path.basename(path)}")

    def clear_zones(self):
        self.zone_manager.clear_zones()
        self.update_zone_list()
        self.status_bar.showMessage("All zones cleared")

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        if self.detection_engine:
            self.detection_engine.cleanup()
        event.accept()

