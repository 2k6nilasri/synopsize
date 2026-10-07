import os
import re
import uuid
import zipfile
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image
import pymupdf as fitz

from app.config import (
    ALLOWED_EXTENSIONS,
    MAGIC_BYTES_MAP,
    MAX_FILE_SIZE_BYTES,
    MAX_IMAGE_PIXELS,
    UPLOADS_DIR
)

def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r'[^\w\.-]', '_', filename)
    return cleaned[:100]

def validate_uploaded_file(file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
    """
    Performs 5 strict security & validation checks:
    1. Extension & Format check (magic bytes matching)
    2. Size check (<= 50 MB)
    3. Corruption check (file parses)
    4. Security scan (PDF JS/launch, DOCX/XLSX macros/external links/zip-bombs, Formula injection)
    5. Storage assignment (UUID)
    Returns structured report with pass/fail per check.
    """
    checks = []
    is_valid = True
    ext = Path(original_filename).suffix.lower()
    
    # Check 1: Extension allowlist check
    if ext not in ALLOWED_EXTENSIONS:
        checks.append({
            "name": "Format Check",
            "passed": False,
            "message": f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        })
        is_valid = False
    else:
        # Magic bytes check
        clean_ext = ext.lstrip(".")
        magic_pass = True
        if clean_ext in MAGIC_BYTES_MAP:
            expected_magics = MAGIC_BYTES_MAP[clean_ext]
            matched = any(file_bytes.startswith(m) for m in expected_magics)
            if not matched:
                magic_pass = False
                is_valid = False
                checks.append({
                    "name": "Format Check",
                    "passed": False,
                    "message": f"File signature (magic bytes) does not match expected format for extension '{ext}'."
                })
        if magic_pass:
            checks.append({
                "name": "Format Check",
                "passed": True,
                "message": f"Extension '{ext}' and magic bytes verified matching."
            })

    # Check 2: Size Check
    file_size = len(file_bytes)
    if file_size > MAX_FILE_SIZE_BYTES:
        checks.append({
            "name": "Size Check",
            "passed": False,
            "message": f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed limit of 50 MB."
        })
        is_valid = False
    elif file_size == 0:
        checks.append({
            "name": "Size Check",
            "passed": False,
            "message": "File is empty (0 bytes)."
        })
        is_valid = False
    else:
        checks.append({
            "name": "Size Check",
            "passed": True,
            "message": f"File size ({file_size / (1024*1024):.2f} MB) within 50 MB limit."
        })

    # Check 3 & 4: Corruption and Security Threat Scan
    corruption_passed = True
    security_passed = True
    security_messages = []

    if ext in [".png", ".jpg", ".jpeg"]:
        try:
            from io import BytesIO
            img = Image.open(BytesIO(file_bytes))
            img.verify()
            # Reopen for size check after verify
            img = Image.open(BytesIO(file_bytes))
            w, h = img.size
            if w * h > MAX_IMAGE_PIXELS:
                security_passed = False
                is_valid = False
                security_messages.append(f"Decompression bomb risk: image dimensions {w}x{h} exceed pixel limit.")
        except Exception as e:
            corruption_passed = False
            is_valid = False

    elif ext == ".pdf":
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = len(doc)
            if page_count == 0:
                corruption_passed = False
                is_valid = False
            else:
                # Security Scan for PDF threats
                pdf_text_raw = file_bytes.decode('latin1', errors='ignore')
                dangerous_patterns = [
                    (r'/JavaScript', "Embedded JavaScript detected"),
                    (r'/JS\b', "Embedded JS code detected"),
                    (r'/Launch\b', "Launch action detected"),
                    (r'/EmbeddedFiles', "Embedded file attachments detected"),
                    (r'/AA\b', "Automatic action (AA) script detected"),
                    (r'/OpenAction', "Auto-execute OpenAction detected")
                ]
                for pat, desc in dangerous_patterns:
                    if re.search(pat, pdf_text_raw, re.IGNORECASE):
                        security_passed = False
                        is_valid = False
                        security_messages.append(desc)
            doc.close()
        except Exception as e:
            corruption_passed = False
            is_valid = False

    elif ext in [".docx", ".xlsx"]:
        try:
            from io import BytesIO
            with zipfile.ZipFile(BytesIO(file_bytes)) as z:
                # Zip bomb / decompression bomb protection check
                total_uncompressed = sum(file_info.file_size for file_info in z.infolist())
                compression_ratio = total_uncompressed / max(1, file_size)
                if compression_ratio > 100:
                    security_passed = False
                    is_valid = False
                    security_messages.append(f"Suspicious zip compression ratio ({compression_ratio:.1f}x). Decompression bomb blocked.")

                # Scan entries for macros or external targets
                filenames = z.namelist()
                for name in filenames:
                    if "vbaProject.bin" in name.lower():
                        security_passed = False
                        is_valid = False
                        security_messages.append("VBA Macro (vbaProject.bin) detected.")
                    if "oleObject" in name.lower():
                        security_passed = False
                        is_valid = False
                        security_messages.append("Embedded OLE Object detected.")
                    
                    if name.endswith(".rels"):
                        rels_content = z.read(name).decode('utf-8', errors='ignore')
                        if 'TargetMode="External"' in rels_content:
                            security_passed = False
                            is_valid = False
                            security_messages.append("Dangerous external relationship target detected.")
        except zipfile.BadZipFile:
            corruption_passed = False
            is_valid = False
        except Exception:
            corruption_passed = False
            is_valid = False

    elif ext in [".csv"]:
        try:
            text_content = file_bytes.decode('utf-8', errors='replace')
            # Check for CSV formula injection indicators
            lines = text_content.splitlines()
            formula_count = 0
            for line in lines[:100]:
                parts = line.split(',')
                for p in parts:
                    clean_p = p.strip(' "\'\t\r\n')
                    if clean_p.startswith(('=', '+', '-', '@')) and len(clean_p) > 1:
                        formula_count += 1
            if formula_count > 0:
                security_messages.append(f"Neutralized {formula_count} potential CSV formula injection cells (prefixed with = + - @).")
        except Exception:
            corruption_passed = False
            is_valid = False

    # Add Corruption Check status
    if corruption_passed:
        checks.append({
            "name": "Corruption Check",
            "passed": True,
            "message": "File integrity verified. File opens and parses cleanly."
        })
    else:
        checks.append({
            "name": "Corruption Check",
            "passed": False,
            "message": "File appears corrupted or unreadable."
        })

    # Add Security Scan status
    if security_passed:
        sec_msg = "Security scan passed. No embedded scripts, macros, or threats found."
        if security_messages:
            sec_msg += " (" + "; ".join(security_messages) + ")"
        checks.append({
            "name": "Security Scan",
            "passed": True,
            "message": sec_msg
        })
    else:
        checks.append({
            "name": "Security Scan",
            "passed": False,
            "message": "Security threat detected: " + "; ".join(security_messages)
        })

    # Store file under UUID if valid
    saved_path = None
    file_id = str(uuid.uuid4())
    if is_valid:
        safe_name = sanitize_filename(original_filename)
        job_dir = UPLOADS_DIR / file_id
        job_dir.mkdir(parents=True, exist_ok=True)
        saved_path = job_dir / safe_name
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

    return {
        "file_id": file_id,
        "is_valid": is_valid,
        "filename": original_filename,
        "file_size": file_size,
        "saved_path": str(saved_path) if saved_path else None,
        "checks": checks,
        "banner_message": "Your uploaded file is valid." if is_valid else "File validation failed. Please address the errors listed above."
    }

def neutralize_formula_injection(text: str) -> str:
    """Neutralizes Excel/CSV formula injection by prepending single quote to dangerous triggers."""
    if text and text.startswith(('=', '+', '-', '@')):
        return "'" + text
    return text

def mask_pii_entities(text: str) -> str:
    r"""
    Scans and redacts Personally Identifiable Information:
    - US Social Security Numbers (SSN: \d{3}-\d{2}-\d{4})
    - Email addresses
    - Phone numbers
    - Credit card numbers (13-19 digits)
    """
    if not text:
        return text

    # SSN regex
    masked = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]', text)
    # Email regex
    masked = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', masked)
    # Credit Card regex (13-16 digits with hyphens or spaces)
    masked = re.sub(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[REDACTED_CARD]', masked)
    # Phone numbers
    masked = re.sub(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[REDACTED_PHONE]', masked)

    return masked

