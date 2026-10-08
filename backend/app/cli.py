import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict

import yaml

from app.config import CONFIG_FILE, MAX_FILE_SIZE_BYTES
from app.core.audit import append_audit_event
from app.core.file_parser import extract_document
from app.core.output import normalize_document, render_markdown, save_figure_assets
from app.core.security import validate_uploaded_file
from app.core.semantic.chunker import create_semantic_chunks
from app.core.semantic.indexer import VectorIndex


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _error(stage: int, stage_name: str, code: str, message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "stage": stage,
        "stage_name": stage_name,
        "code": code,
        "message": message,
        "recoverable": False,
    }


def _load_config(config_path: Path) -> Dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError(f"Configuration must be a YAML object: {config_path}")
    return config


def parse_file(
    input_path: Path,
    output_dir: Path,
    config_path: Path = CONFIG_FILE,
    no_embeddings: bool = False,
) -> int:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(exist_ok=True)

    try:
        config = _load_config(config_path)
        file_bytes = input_path.read_bytes()
    except (OSError, ValueError, yaml.YAMLError) as error:
        failure = _error(1, "Secure Upload", "INPUT_ERROR", str(error))
        _write_json(output_dir / "result.json", failure)
        _write_json(output_dir / "report.json", failure)
        print(json.dumps(failure), file=sys.stderr)
        return 2

    configured_limit = int(
        config.get("upload", {}).get("max_file_size_bytes", MAX_FILE_SIZE_BYTES)
    )
    if len(file_bytes) > configured_limit:
        failure = _error(
            1,
            "Secure Upload",
            "FILE_TOO_LARGE",
            f"File size exceeds the configured {configured_limit}-byte limit.",
        )
        _write_json(output_dir / "result.json", failure)
        _write_json(output_dir / "report.json", failure)
        print(json.dumps(failure), file=sys.stderr)
        return 2

    validation = validate_uploaded_file(file_bytes, input_path.name, store=False)
    if not validation["is_valid"]:
        failure = _error(
            2,
            "File Validation",
            "INVALID_FILE",
            validation["banner_message"],
        )
        failure["checks"] = validation["checks"]
        _write_json(output_dir / "result.json", failure)
        _write_json(output_dir / "report.json", failure)
        print(json.dumps(failure), file=sys.stderr)
        return 2

    document_id = str(uuid.uuid4())
    try:
        parsed = extract_document(file_bytes, input_path.name)
    except Exception as error:
        failure = _error(7, "Document Extraction", "EXTRACTION_FAILED", str(error))
        _write_json(output_dir / "result.json", failure)
        _write_json(output_dir / "report.json", failure)
        print(json.dumps(failure), file=sys.stderr)
        return 1

    normalize_document(parsed, file_bytes, input_path.name, document_id)
    save_figure_assets(parsed["pages"], output_dir)
    chunks = create_semantic_chunks(parsed["pages"])
    if not no_embeddings:
        chunks = VectorIndex(chunks).chunks
    markdown = render_markdown(input_path.name, parsed["pages"])
    result = {
        "document_id": document_id,
        "filename": input_path.name,
        "file_type": input_path.suffix.lower().lstrip("."),
        "file_size": len(file_bytes),
        "file_sha256": parsed["file_sha256"],
        "total_pages": parsed["total_pages"],
        "pages": parsed["pages"],
        "child_documents": parsed.get("child_documents", []),
        "revisions": parsed.get("revisions", []),
        "comments": parsed.get("comments", []),
        "footnotes": parsed.get("footnotes", []),
        "endnotes": parsed.get("endnotes", []),
        "markdown": markdown,
        "ocr_text": parsed["ocr_text"],
        "chunks": chunks,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "processing_time_seconds": round(time.perf_counter() - started, 3),
    }
    report = {
        "status": "complete",
        "validation": validation,
        "review_flags": [
            block["id"]
            for page in parsed["pages"]
            for block in page["blocks"]
            if "needs_review" in block.get("flags", [])
        ],
        "chunk_count": len(chunks),
        "embeddings_enabled": not no_embeddings,
        "processing_time_seconds": result["processing_time_seconds"],
    }

    _write_json(output_dir / "result.json", result)
    (output_dir / "result.md").write_text(markdown, encoding="utf-8")
    (output_dir / "ocr.txt").write_text(parsed["ocr_text"], encoding="utf-8")
    (output_dir / "chunks.jsonl").write_text(
        "".join(json.dumps(chunk, ensure_ascii=False, default=str) + "\n" for chunk in chunks),
        encoding="utf-8",
    )
    _write_json(output_dir / "report.json", report)
    audit_entry = append_audit_event(
        document_id,
        "cli_parse",
        "completed",
        parsed["file_sha256"],
        stage=13,
    )
    result["audit_entry_hash"] = audit_entry["entry_hash"]
    report["audit_entry_hash"] = audit_entry["entry_hash"]
    _write_json(output_dir / "result.json", result)
    _write_json(output_dir / "report.json", report)
    print(json.dumps({"status": "complete", "output": str(output_dir), "pages": result["total_pages"]}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="parse",
        description="Parse a supported document and write structured outputs.",
    )
    parser.add_argument("file", type=Path, help="Input document")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    parser.add_argument("--config", type=Path, default=CONFIG_FILE, help="YAML config file")
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Write semantic chunks without calculating embeddings.",
    )
    args = parser.parse_args()
    return parse_file(args.file, args.out, args.config, args.no_embeddings)


if __name__ == "__main__":
    raise SystemExit(main())
