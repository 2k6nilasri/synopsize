import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import CORRECTIONS_DIR

CORRECTIONS_FILE = CORRECTIONS_DIR / "corrections.jsonl"
CONSENT_FILE = CORRECTIONS_DIR / "consent_settings.json"

def get_correction_consent() -> bool:
    """Returns user consent preference (default True)."""
    if CONSENT_FILE.exists():
        try:
            with open(CONSENT_FILE, "r") as f:
                data = json.load(f)
                return data.get("consent_enabled", True)
        except Exception:
            return True
    return True

def set_correction_consent(enabled: bool):
    """Sets user consent preference."""
    with open(CONSENT_FILE, "w") as f:
        json.dump({"consent_enabled": enabled}, f)

def log_correction(
    original_text: str,
    corrected_text: str,
    page: int,
    bbox: list,
    extractor: str,
    confidence: float,
    cropped_image_base64: Optional[str] = None
) -> Dict[str, Any]:
    """
    Silently logs low-confidence block corrections for future fine-tuning.
    Only logs if user consent is enabled.
    """
    if not get_correction_consent():
        return {"status": "skipped", "reason": "User opted out of correction logging."}

    correction_record = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "original_text": original_text,
        "corrected_text": corrected_text,
        "page": page,
        "bbox": bbox,
        "extractor": extractor,
        "confidence": confidence,
        "cropped_image_base64": cropped_image_base64
    }

    with open(CORRECTIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(correction_record) + "\n")

    return {"status": "logged", "record": correction_record}
