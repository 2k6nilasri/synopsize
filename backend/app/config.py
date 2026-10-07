import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
JOBS_DIR = STORAGE_DIR / "jobs"
CORRECTIONS_DIR = STORAGE_DIR / "corrections"
TOOLS_DIR = STORAGE_DIR / "tools_output"

for d in [STORAGE_DIR, UPLOADS_DIR, JOBS_DIR, CORRECTIONS_DIR, TOOLS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Confidence Indicators Configuration
CONFIDENCE_RED_MAX = 0.6999       # Below 0.70
CONFIDENCE_YELLOW_MIN = 0.70
CONFIDENCE_YELLOW_MAX = 0.8999
CONFIDENCE_GREEN_MIN = 0.90       # 0.90 and above

def get_confidence_level(score: float) -> str:
    if score < 0.70:
        return "red"
    elif score < 0.90:
        return "yellow"
    else:
        return "green"

# Security & Upload limits
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit
MAX_PAGES = 100
MAX_IMAGE_PIXELS = 100_000_000
RETENTION_HOURS = 24

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".xlsx", ".csv"}

MAGIC_BYTES_MAP = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "docx": [b"PK\x03\x04"],  # Zip container
    "xlsx": [b"PK\x03\x04"],  # Zip container
}
