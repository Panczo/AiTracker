"""Configuration settings for the AiTracker application."""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
PROCESSED_DIR = STORAGE_DIR / "processed"
MODELS_DIR = STORAGE_DIR / "models"
DATABASE_PATH = STORAGE_DIR / "aitracker.db"

# Ensure directories exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# File size limits
MAX_FILE_SIZE_MB = 250
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_TOTAL_DURATION_HOURS = 24  # Maximum total video duration for batch

# Allowed video formats
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# Time interval settings
INTERVAL_MINUTES = 5  # Report intervals in minutes
SECONDS_PER_INTERVAL = INTERVAL_MINUTES * 60

# Vehicle classification (8+1 categories)
VEHICLE_CLASSES = {
    'motocykl': {'coco_classes': [3], 'label': 'Motocykl'},  # motorcycle
    'samochod_osobowy': {'coco_classes': [2], 'label': 'Samochód osobowy'},  # car
    'samochod_dostawczy': {'coco_classes': [7], 'label': 'Samochód dostawczy'},  # truck (light)
    'samochod_ciezarowy': {'coco_classes': [7], 'label': 'Samochód ciężarowy'},  # truck (heavy)
    'autobus': {'coco_classes': [5], 'label': 'Autobus'},  # bus
    'rower': {'coco_classes': [1], 'label': 'Rower'},  # bicycle
    'ciagnik': {'coco_classes': [7], 'label': 'Ciągnik'},  # tractor (will need fine-tuning)
    'przyczepa': {'coco_classes': [7], 'label': 'Przyczepa'},  # trailer (will need fine-tuning)
    'inne': {'coco_classes': [], 'label': 'Inne'},  # other/unknown
}

# COCO class mapping to our categories
COCO_TO_VEHICLE = {
    1: 'rower',  # bicycle
    2: 'samochod_osobowy',  # car
    3: 'motocykl',  # motorcycle
    5: 'autobus',  # bus
    7: 'samochod_dostawczy',  # truck (default to delivery, can be refined)
}

# YOLO settings
YOLO_MODEL = "yolo11n.pt"  # nano model for CPU
YOLO_CONFIDENCE = 0.25
YOLO_IOU = 0.45

# Tracking settings
TRACK_PERSISTENCE = 30  # frames to keep track alive without detection

# Processing settings
FRAME_SKIP = 1  # Process every Nth frame (1 = all frames)
OUTPUT_VIDEO_CODEC = "mp4v"
OUTPUT_VIDEO_FPS = 30

# Anonymization settings
BLUR_KERNEL_SIZE = 51  # Size of blur kernel (must be odd)
FACE_CONFIDENCE = 0.5  # Minimum confidence for face detection
PLATE_CONFIDENCE = 0.3  # Minimum confidence for license plate detection

# Line crossing settings
LINE_CROSSING_TOLERANCE = 10  # Pixels tolerance for line crossing detection

# Database settings
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"
