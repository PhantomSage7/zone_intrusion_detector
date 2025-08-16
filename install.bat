@echo off
echo Setting up Zone Intrusion Detector for Windows...

:: Create virtual environment
python -m venv venv
call venv\Scripts\activate

:: Install compatible PyTorch version
pip install torch==2.0.1+cu117 torchvision==0.15.2+cu117 --index-url https://download.pytorch.org/whl/cu117

:: Install other dependencies
pip install -r requirements.txt

:: Download model
python -c "from src.model_utils import download_model; download_model('https://github.com/ultralytics/assets/releases/download/v8.0.0/yolov8n.pt', 'models/yolov8n.pt')"

echo Setup complete!
echo Run the application with: python src\main.py
pause