import csv
import hashlib
import io
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from app.config import AUDIT_LOG_FILE

_LOCK = threading.Lock()
_GENESIS_HASH = "0" * 64


def _canonical_json(record: Dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _last_hash() -> str:
    if not AUDIT_LOG_FILE.exists():
        return _GENESIS_HASH
    last_entry = None
    with AUDIT_LOG_FILE.open("r", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                last_entry = json.loads(line)
    return last_entry.get("entry_hash", _GENESIS_HASH) if last_entry else _GENESIS_HASH


def append_audit_event(
    job_id: str,
    event: str,
    status: str,
    file_sha256: str = "",
    stage: int = 0,
) -> Dict[str, Any]:
    with _LOCK:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "event": event,
            "status": status,
            "file_sha256": file_sha256,
            "stage": stage,
            "previous_hash": _last_hash(),
        }
        record["entry_hash"] = hashlib.sha256(
            _canonical_json(record).encode("utf-8")
        ).hexdigest()
        with AUDIT_LOG_FILE.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record


def read_audit_log() -> List[Dict[str, Any]]:
    if not AUDIT_LOG_FILE.exists():
        return []
    with AUDIT_LOG_FILE.open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def verify_audit_log(records: List[Dict[str, Any]] | None = None) -> Tuple[bool, int]:
    previous_hash = _GENESIS_HASH
    if records is None:
        records = read_audit_log()
    for index, record in enumerate(records, start=1):
        entry_hash = record.get("entry_hash", "")
        unsigned_record = {key: value for key, value in record.items() if key != "entry_hash"}
        expected_hash = hashlib.sha256(
            _canonical_json(unsigned_record).encode("utf-8")
        ).hexdigest()
        if record.get("previous_hash") != previous_hash or entry_hash != expected_hash:
            return False, index
        previous_hash = entry_hash
    return True, len(records)


def audit_csv(records: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    fields = ["timestamp", "job_id", "event", "status", "file_sha256", "stage", "previous_hash", "entry_hash"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()
