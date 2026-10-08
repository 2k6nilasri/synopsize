import logging
import time
from pathlib import Path
from typing import Iterable

from app.config import JOBS_DIR, RETENTION_HOURS, TOOLS_DIR, UPLOADS_DIR

logger = logging.getLogger(__name__)


def cleanup_expired_artifacts(
    now: float | None = None,
    retention_hours: int = RETENTION_HOURS,
    storage_directories: Iterable[Path] = (UPLOADS_DIR, JOBS_DIR, TOOLS_DIR),
) -> int:
    cutoff = (time.time() if now is None else now) - retention_hours * 3600
    removed = 0
    for directory in storage_directories:
        if not directory.exists():
            continue
        for entry in directory.iterdir():
            if entry.is_file():
                if entry.stat().st_mtime < cutoff:
                    entry.unlink()
                    removed += 1
                continue
            if not entry.is_dir():
                continue
            for child in entry.iterdir():
                if child.is_file() and child.stat().st_mtime < cutoff:
                    child.unlink()
                    removed += 1
            if not any(entry.iterdir()):
                entry.rmdir()
    if removed:
        logger.info("Removed %d expired upload/result/tool files.", removed)
    return removed
