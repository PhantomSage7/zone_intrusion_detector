#zone_intrusion_detector\src\main.py
import sys
import logging
import yaml
from PyQt5.QtWidgets import QApplication, QMessageBox
from src.gui import MainWindow
from src.logger import EventLogger  # Import EventLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# PyTorch compatibility
import torch
torch.set_float32_matmul_precision('high')

def load_config():
    try:
        with open("config/settings.yaml", "r") as f:
            settings = yaml.safe_load(f)
        with open("config/zone_colors.yaml", "r") as f:
            zone_colors = yaml.safe_load(f)
        return settings, zone_colors
    except Exception as e:
        logger.exception("Failed to load configuration")
        raise

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        settings, zone_colors = load_config()
        
        # Create event logger
        event_logger = EventLogger()
        
        window = MainWindow(settings, zone_colors, event_logger)  # Pass to MainWindow
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.exception("Unhandled exception in application")
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"Application failed to start:\n{str(e)}\n\nCheck app.log for details."
        )
        sys.exit(1)