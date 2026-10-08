import hashlib
import datetime
import base64
import re
from pathlib import Path
from typing import Any, Dict, List

from app.config import get_confidence_level


def normalize_document(
    parsed: Dict[str, Any], file_bytes: bytes, filename: str, document_id: str
) -> Dict[str, Any]:
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    source_format = Path(filename).suffix.lower().lstrip(".")
    parsed["file_sha256"] = file_hash

    _normalize_pages(
        parsed,
        filename,
        source_format,
        file_hash,
        timestamp,
        document_id,
        None,
    )
    return parsed


def _normalize_pages(
    document: Dict[str, Any],
    filename: str,
    source_format: str,
    file_hash: str,
    timestamp: str,
    document_id: str,
    parent_id: str | None,
) -> None:
    document.setdefault("document_id", document_id)
    if parent_id:
        document["parent_id"] = parent_id
    for page_index, page in enumerate(document.get("pages", []), start=1):
        page_number = page.get("page_number", page_index)
        page["page_number"] = page_number
        page_type = page.get("page_type") or (
            "image" if source_format in {"png", "jpg", "jpeg", "tif", "tiff", "heic"} else "document"
        )
        page["page_type"] = page_type
        for reading_order, block in enumerate(page.get("blocks", []), start=1):
            confidence = float(block.get("confidence", 0.0))
            confidence = min(1.0, max(0.0, confidence))
            extractor = block.get("extractor", "unknown")
            block["id"] = block.get("id") or f"block-{page_number}-{reading_order}"
            block["type"] = block.get("type", "paragraph")
            block["page"] = page_number
            block["bbox"] = block.get("bbox") or [0, 0, 0, 0]
            block["bbox_unit"] = block.get("bbox_unit", "px")
            block["origin"] = block.get("origin", "top-left")
            block["reading_order"] = reading_order
            block["confidence"] = round(confidence, 4)
            block["confidence_level"] = get_confidence_level(confidence)
            block["confidence_basis"] = (
                "ocr_engine_score"
                if "tesseract" in str(extractor).lower()
                else "heuristic_extractor_estimate"
            )
            block["confidence_calibrated"] = False
            block.setdefault("content", "")
            block["extractor"] = extractor
            block.setdefault(
                "routing", [{"tried": extractor, "confidence": block["confidence"]}]
            )
            block.setdefault("spans_pages", [page_number])
            block.setdefault("provenance", {})
            block["provenance"].update(
                {
                    "file_sha256": file_hash,
                    "source_format": source_format,
                    "page_type": page_type,
                    "timestamp": timestamp,
                }
            )
            flags = list(block.get("flags", []))
            if confidence < 0.70 and "needs_review" not in flags:
                flags.append("needs_review")
            block["flags"] = flags

    for child in document.get("child_documents", []):
        if not child.get("pages"):
            continue
        child_hash = child.get("file_sha256", file_hash)
        child_format = Path(child.get("filename", filename)).suffix.lower().lstrip(".")
        _normalize_pages(
            child,
            child.get("filename", filename),
            child_format,
            child_hash,
            timestamp,
            child.get("document_id", f"{document_id}-attachment"),
            document_id,
        )


def render_markdown(filename: str, pages: List[Dict[str, Any]]) -> str:
    lines = [f"# Document Analysis: {filename}"]
    for page in pages:
        lines.append(f"\n## Page {page['page_number']}")
        for block in page.get("blocks", []):
            block_type = block.get("type")
            if block_type == "header_footer":
                continue
            content = str(block.get("content", "")).strip()
            if not content:
                continue
            if block_type == "heading":
                lines.append(f"\n### {content}")
            elif block_type in {"table", "equation", "code"}:
                lines.append(f"\n{content}")
            elif block_type == "list" and not content.startswith(("-", "*", "+")):
                lines.append(f"- {content}")
            else:
                lines.append(content)
    return "\n".join(lines).strip() + "\n"


def save_figure_assets(pages: List[Dict[str, Any]], output_dir: Path) -> None:
    data_uri = re.compile(
        r"data:image/([\w.+-]+);base64,([A-Za-z0-9+/=]+)", re.IGNORECASE
    )
    for page in pages:
        for block in page.get("blocks", []):
            content = str(block.get("content", ""))
            metadata = block.setdefault("metadata", {})
            image_data = metadata.get("image_data")
            match = data_uri.search(content) or (
                data_uri.fullmatch(image_data) if isinstance(image_data, str) else None
            )
            if not match:
                continue
            extension = match.group(1).lower().replace("jpeg", "jpg")
            filename = f"page-{page['page_number']:03d}-block-{block['reading_order']:03d}.{extension}"
            asset_path = output_dir / "figures" / filename
            asset_path.write_bytes(base64.b64decode(match.group(2)))
            relative_path = f"figures/{filename}"
            block["content"] = data_uri.sub(relative_path, content, count=1)
            metadata["image_path"] = relative_path
            metadata.pop("image_data", None)
