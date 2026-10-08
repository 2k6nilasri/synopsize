import io
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from app.config import ALLOWED_EXTENSIONS, EXTRACTOR_TIMEOUT_SECONDS
from app.core.extractors.docx_extractor import process_docx_document
from app.core.extractors.excel_extractor import process_excel_or_csv
from app.core.extractors.image_extractor import process_image_file
from app.core.extractors.pdf_extractor import process_pdf_document
from app.core.extractors.pptx_extractor import process_pptx_document
from app.core.extractors.text_extractor import process_text_document

try:
    import pillow_heif
except ImportError:
    pillow_heif = None
else:
    pillow_heif.register_heif_opener()


LEGACY_CONVERSIONS = {
    ".doc": ".docx",
    ".ppt": ".pptx",
    ".xls": ".xlsx",
}


def extract_document(
    file_bytes: bytes,
    filename: str,
    depth: int = 0,
    attachment_state: Optional[List[int]] = None,
) -> Dict[str, Any]:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format: {extension or '(no extension)'}")
    state = attachment_state if attachment_state is not None else [0]

    if extension in LEGACY_CONVERSIONS:
        converted_bytes, converted_name = _convert_legacy_office(file_bytes, filename, extension)
        return extract_document(converted_bytes, converted_name, depth, state)
    if extension == ".pdf":
        return process_pdf_document(file_bytes, filename)
    if extension in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic"}:
        return _process_image_document(file_bytes, filename)
    if extension == ".docx":
        return process_docx_document(file_bytes, filename)
    if extension == ".pptx":
        return process_pptx_document(file_bytes, filename)
    if extension in {".xlsx", ".xls", ".csv"}:
        return process_excel_or_csv(file_bytes, filename)
    return process_text_document(
        file_bytes,
        filename,
        attachment_parser=_parse_attachment,
        attachment_depth=depth,
        attachment_state=state,
    )


def _parse_attachment(
    file_bytes: bytes, filename: str, depth: int, attachment_state: List[int]
) -> Dict[str, Any]:
    try:
        return extract_document(file_bytes, filename, depth, attachment_state)
    except ValueError as error:
        return {
            "filename": filename,
            "status": "error",
            "error": {
                "status": "error",
                "stage": 2,
                "stage_name": "File Validation",
                "code": "UNSUPPORTED_FORMAT",
                "message": str(error),
                "recoverable": True,
            },
        }


def _process_image_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    image = Image.open(io.BytesIO(file_bytes))
    pages: List[Dict[str, Any]] = []
    ocr_lines: List[str] = []
    for page_number in range(getattr(image, "n_frames", 1)):
        image.seek(page_number)
        frame = image.convert("RGB")
        buffer = io.BytesIO()
        frame.save(buffer, format="PNG")
        parsed = process_image_file(buffer.getvalue(), filename)
        page = parsed["pages"][0]
        page["page_number"] = page_number + 1
        for block_number, block in enumerate(page["blocks"], start=1):
            block["id"] = f"block-{page_number + 1}-{block_number}"
            block["page"] = page_number + 1
            block["reading_order"] = block_number
        pages.append(page)
        ocr_lines.append(f"--- Page {page_number + 1} ---")
        ocr_lines.append(parsed["ocr_text"])
    image.close()
    return {
        "total_pages": len(pages),
        "pages": pages,
        "ocr_text": "\n".join(ocr_lines),
    }


def _convert_legacy_office(
    file_bytes: bytes, filename: str, extension: str
) -> tuple[bytes, str]:
    libreoffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not libreoffice:
        raise RuntimeError(
            f"Converting {extension} files requires LibreOffice (soffice) on PATH."
        )

    target_extension = LEGACY_CONVERSIONS[extension]
    with tempfile.TemporaryDirectory(prefix="synopsize-convert-") as temp_dir:
        source = Path(temp_dir) / f"source{extension}"
        source.write_bytes(file_bytes)
        completed = subprocess.run(
            [
                libreoffice,
                "--headless",
                "--convert-to",
                target_extension.lstrip("."),
                "--outdir",
                temp_dir,
                str(source),
            ],
            capture_output=True,
            text=True,
            timeout=EXTRACTOR_TIMEOUT_SECONDS,
            check=False,
        )
        converted = Path(temp_dir) / f"source{target_extension}"
        if completed.returncode != 0 or not converted.is_file():
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"LibreOffice could not convert {filename} to {target_extension}: "
                f"{detail or 'conversion produced no output'}"
            )
        return converted.read_bytes(), converted.name
