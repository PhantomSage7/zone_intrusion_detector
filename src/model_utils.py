#zone_intrusion_detector\src\model_utils.py
import os
import requests
import hashlib
from tqdm import tqdm
import logging

# Corrected model URL
MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
MODEL_MD5 = "0305608151dd1725c9d7da6882ae52d5"

logger = logging.getLogger(__name__)

def get_model_path(config):
    """Get model path and ensure it exists with correct checksum"""
    model_path = config["detection"]["model"]
    model_dir = os.path.dirname(model_path)
    
    # Create directory if needed
    os.makedirs(model_dir, exist_ok=True)
    
    # Download if file doesn't exist
    if not os.path.exists(model_path):
        download_model(MODEL_URL, model_path)
    
    # Verify model integrity
    if not verify_model(model_path):
        logger.error("Model verification failed. Re-downloading...")
        os.remove(model_path)
        download_model(MODEL_URL, model_path)
        
        if not verify_model(model_path):
            raise RuntimeError("Failed to download valid model file")
    
    return model_path

def download_model(url, save_path):
    """Download model with progress bar - Windows compatible"""
    logger.info(f"Downloading model from {url}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1KB chunks
        
        with open(save_path, 'wb') as f:
            with tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
                desc=f"Downloading {os.path.basename(save_path)}"
            ) as bar:
                for data in response.iter_content(block_size):
                    bar.update(len(data))
                    f.write(data)
        logger.info("Download completed successfully")
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise RuntimeError(f"Model download failed: {str(e)}")

def download_test_video():
    video_url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/people-detection.mp4"
    video_path = "data/test_video.mp4"
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    
    if not os.path.exists(video_path):
        print("Downloading test video...")
        try:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024  # 1KB chunks
            
            with open(video_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    f.write(data)
            print("Test video downloaded successfully")
        except Exception as e:
            print(f"Failed to download test video: {str(e)}")
    return video_path

def verify_model(model_path):
    """Verify model integrity using MD5 checksum"""
    if not MODEL_MD5:
        return True  # Skip verification if no MD5 provided
    
    try:
        # Calculate file MD5
        md5_hash = hashlib.md5()
        with open(model_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        
        file_md5 = md5_hash.hexdigest()
        if file_md5 != MODEL_MD5:
            logger.warning(f"Model MD5 mismatch: expected {MODEL_MD5}, got {file_md5}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return False