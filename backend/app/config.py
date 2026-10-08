import os
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.yaml"
with CONFIG_FILE.open("r", encoding="utf-8") as config_stream:
    SETTINGS = yaml.safe_load(config_stream) or {}

STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
JOBS_DIR = STORAGE_DIR / "jobs"
CORRECTIONS_DIR = STORAGE_DIR / "corrections"
TOOLS_DIR = STORAGE_DIR / "tools_output"
AUDIT_LOG_FILE = STORAGE_DIR / "audit.jsonl"

for d in [STORAGE_DIR, UPLOADS_DIR, JOBS_DIR, CORRECTIONS_DIR, TOOLS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Confidence Indicators Configuration
CONFIDENCE_RED_MAX = float(SETTINGS["confidence"]["red_max"])
CONFIDENCE_YELLOW_MAX = float(SETTINGS["confidence"]["yellow_max"])

def get_confidence_level(score: float) -> str:
    if score < CONFIDENCE_RED_MAX:
        return "red"
    elif score < CONFIDENCE_YELLOW_MAX:
        return "yellow"
    else:
        return "green"

# Security & Upload limits
MAX_FILE_SIZE_BYTES = int(SETTINGS["upload"]["max_file_size_bytes"])
MAX_PAGES = int(SETTINGS["upload"]["max_pages"])
MAX_IMAGE_PIXELS = int(SETTINGS["upload"]["max_image_pixels"])
MAX_ARCHIVE_UNCOMPRESSED_BYTES = int(
    SETTINGS["upload"]["max_archive_uncompressed_bytes"]
)
MAX_ATTACHMENT_DEPTH = int(SETTINGS["upload"]["max_attachment_depth"])
MAX_ATTACHMENT_BYTES = int(SETTINGS["upload"]["max_attachment_bytes"])
RETENTION_HOURS = int(SETTINGS["retention"]["hours"])
RETENTION_CLEANUP_INTERVAL_SECONDS = int(
    SETTINGS["retention"]["cleanup_interval_seconds"]
)
EXTRACTOR_TIMEOUT_SECONDS = int(SETTINGS["processing"]["extractor_timeout_seconds"])
ANTIVIRUS_SETTINGS = SETTINGS["security"].get("antivirus", {})
ANTIVIRUS_MODE = os.environ.get(
    "SYNOPSIZE_ANTIVIRUS_MODE",
    str(ANTIVIRUS_SETTINGS.get("mode", "disabled")),
).lower()
CLAMD_HOST = os.environ.get(
    "SYNOPSIZE_CLAMD_HOST",
    str(ANTIVIRUS_SETTINGS.get("host", "127.0.0.1")),
)
CLAMD_PORT = int(os.environ.get(
    "SYNOPSIZE_CLAMD_PORT",
    ANTIVIRUS_SETTINGS.get("port", 3310),
))
CLAMD_TIMEOUT_SECONDS = float(ANTIVIRUS_SETTINGS.get("timeout_seconds", 15))

if ANTIVIRUS_MODE not in {"disabled", "optional", "required"}:
    raise ValueError(
        "SYNOPSIZE_ANTIVIRUS_MODE must be disabled, optional, or required."
    )

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic",
    ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv",
    ".html", ".htm", ".md", ".txt", ".rtf", ".eml", ".msg",
}

MAGIC_BYTES_MAP = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "tif": [b"II*\x00", b"MM\x00*"],
    "tiff": [b"II*\x00", b"MM\x00*"],
    "heic": [b"ftypheic", b"ftypheix", b"ftyphevc", b"ftyphevx", b"ftypmif1", b"ftypmsf1"],
    "docx": [b"PK\x03\x04"],  # Zip container
    "pptx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],  # Zip container
    "doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    "ppt": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    "xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    "msg": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
}
