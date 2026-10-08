import os
import io
import json
import zipfile
import pytest
import numpy as np
import cv2
import pymupdf as fitz
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    get_confidence_level
)
from app.core.security import (
    validate_uploaded_file,
    sanitize_filename,
    neutralize_formula_injection,
    mask_pii_entities
)
from app.core.extractors.pdf_extractor import process_pdf_document
from app.core.extractors.docx_extractor import process_docx_document
from app.core.extractors.excel_extractor import process_excel_or_csv
from app.core.extractors.image_extractor import process_image_file
from app.core.semantic.chunker import create_semantic_chunks
from app.core.semantic.indexer import VectorIndex
from app.core.corrections import (
    log_correction,
    get_correction_consent,
    set_correction_consent
)
import app.core.corrections as correction_store
import app.core.audit as audit_store

# 8 Image Tools
from app.core.tools.deskew import deskew_image
from app.core.tools.denoise import denoise_image
from app.core.tools.sharpen import sharpen_image
from app.core.tools.rotate import rotate_image, detect_orientation_angle
from app.core.tools.contrast import adjust_contrast
from app.core.tools.blank_detect import is_page_blank, detect_blank_pages_pdf
from app.core.tools.duplicate_detect import detect_duplicate_pages, compute_dhash
from app.core.tools.render_pdf import render_pdf_to_png_zip

client = TestClient(app)

# Helper generators for synthetic test files
def create_test_pdf_bytes(num_pages=2, text="SYNOPSIZE Intelligence Engine Test Document"):
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=612, height=792)
        page.insert_text((50, 72), f"Page {i+1} Heading: Universal Document Processing", fontsize=16)
        page.insert_text((50, 110), f"{text} - Page {i+1} paragraph with deep layout analysis.", fontsize=11)
        # Add sample table text
        page.insert_text((50, 200), "Column1 | Column2 | Column3\n100 | 200 | 300\n400 | 500 | 600", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_test_image_bytes(w=300, h=200, color=(255, 255, 255)):
    img = np.full((h, w, 3), color, dtype=np.uint8)
    cv2.putText(img, "TEST OCR", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()

# ==========================================
# 1. SECURITY & VALIDATION TESTS
# ==========================================

def test_validation_valid_pdf():
    pdf_bytes = create_test_pdf_bytes(1)
    report = validate_uploaded_file(pdf_bytes, "valid_test.pdf", store=False)
    assert report["is_valid"] is True
    assert report["banner_message"] == "Your uploaded file is valid."
    assert all(c["passed"] for c in report["checks"])

def test_validation_invalid_magic_bytes_mismatch():
    fake_pdf = b"NOT_A_REAL_PDF_HEADER_JUST_TEXT"
    report = validate_uploaded_file(fake_pdf, "spoofed.pdf")
    assert report["is_valid"] is False
    assert any("magic bytes" in c["message"].lower() for c in report["checks"])

def test_validation_unsupported_extension():
    report = validate_uploaded_file(b"some content", "malicious_script.exe")
    assert report["is_valid"] is False
    assert any("unsupported file extension" in c["message"].lower() for c in report["checks"])

def test_validation_empty_file():
    report = validate_uploaded_file(b"", "empty.pdf")
    assert report["is_valid"] is False
    assert any("empty" in c["message"].lower() for c in report["checks"])

def test_validation_pdf_javascript_threat_blocked():
    # PDF containing embedded /JavaScript action
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World")
    pdf_bytes = doc.tobytes()
    doc.close()
    
    # Inject /JavaScript trigger
    infected_bytes = pdf_bytes + b"\n/JavaScript << /JS (app.alert('XSS')) >>\n"
    report = validate_uploaded_file(infected_bytes, "threat.pdf")
    assert report["is_valid"] is False
    assert any("javascript detected" in c["message"].lower() for c in report["checks"])

def test_formula_injection_neutralization():
    assert neutralize_formula_injection("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
    assert neutralize_formula_injection("+SUM(A1:A10)") == "'+SUM(A1:A10)"
    assert neutralize_formula_injection("-10+20") == "'-10+20"
    assert neutralize_formula_injection("@SUM(1,2)") == "'@SUM(1,2)"
    assert neutralize_formula_injection("Normal Text") == "Normal Text"

def test_pii_masking():
    text = "User SSN is 123-45-6789, email is analyst@synopsize.ai, and phone is 555-019-2834."
    masked = mask_pii_entities(text)
    assert "[REDACTED_SSN]" in masked
    assert "[REDACTED_EMAIL]" in masked
    assert "123-45-6789" not in masked
    assert "analyst@synopsize.ai" not in masked

# ==========================================
# 2. DOCUMENT EXTRACTORS TESTS
# ==========================================

def test_pdf_extractor_multi_page():
    pdf_bytes = create_test_pdf_bytes(2)
    res = process_pdf_document(pdf_bytes, "sample_multipage.pdf")
    assert res["total_pages"] == 2
    assert len(res["pages"]) == 2
    page1 = res["pages"][0]
    assert page1["page_number"] == 1
    assert "blocks" in page1
    assert len(page1["blocks"]) > 0
    # Bounding boxes format
    for b in page1["blocks"]:
        assert len(b["bbox"]) == 4
        assert b["confidence"] > 0
        assert b["reading_order"] >= 1

def test_image_extractor():
    img_bytes = create_test_image_bytes()
    res = process_image_file(img_bytes, "scan.png")
    assert res["total_pages"] == 1
    assert len(res["pages"]) == 1
    blocks = res["pages"][0]["blocks"]
    assert len(blocks) > 0
    assert any(b["type"] in ["heading", "paragraph"] for b in blocks)

def test_excel_csv_extractor():
    csv_data = 'Name,Role,Score\nAlice,Engineer,"=SUM(10,20)"\nBob,Architect,95\n'
    csv_bytes = csv_data.encode("utf-8")
    res = process_excel_or_csv(csv_bytes, "metrics.csv")
    assert res["total_pages"] == 1
    blocks = res["pages"][0]["blocks"]
    table_block = next((b for b in blocks if b["type"] == "table"), None)
    assert table_block is not None
    # Check that formula '=SUM(10,20)' was neutralized to "'=SUM(10,20)"
    assert "'=SUM(10,20)" in table_block["content"]

# ==========================================
# 3. SEMANTIC CHUNKING & VECTOR SEARCH TESTS
# ==========================================

def test_semantic_chunker_and_vector_index():
    pages = [
        {
            "page_number": 1,
            "blocks": [
                {
                    "id": "block-1-1",
                    "type": "heading",
                    "content": "Deep Learning Architecture Overview",
                    "bbox": [50, 50, 400, 80],
                    "confidence": 0.98
                },
                {
                    "id": "block-1-2",
                    "type": "paragraph",
                    "content": "Transformers utilize self-attention mechanisms to process sequence data efficiently.",
                    "bbox": [50, 90, 500, 150],
                    "confidence": 0.95
                },
                {
                    "id": "block-1-3",
                    "type": "table",
                    "content": "| Layer | Parameters |\n| --- | --- |\n| Encoder | 110M |\n| Decoder | 110M |",
                    "bbox": [50, 160, 500, 300],
                    "confidence": 0.96
                }
            ]
        }
    ]
    chunks = create_semantic_chunks(pages)
    assert len(chunks) >= 1
    assert all("chunk_id" in c for c in chunks)
    assert all("page_range" in c for c in chunks)
    assert all("bounding_boxes" in c for c in chunks)
    
    # Vector indexing & similarity search
    indexer = VectorIndex(chunks)
    assert len(indexer.chunks) == len(chunks)
    
    search_res = indexer.search("self-attention transformers", top_k=2)
    assert len(search_res) > 0
    assert search_res[0]["score"] is not None

# ==========================================
# 4. 8 IMAGE TOOLS UNIT TESTS
# ==========================================

def test_tool_deskew():
    img = np.full((200, 300, 3), 255, dtype=np.uint8)
    cv2.putText(img, "Deskew Test String", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    deskewed = deskew_image(img)
    assert deskewed.shape == img.shape

def test_tool_denoise():
    img = np.full((150, 150, 3), 240, dtype=np.uint8)
    denoised = denoise_image(img, strength=10)
    assert denoised.shape == img.shape

def test_tool_sharpen_preserves_size_and_enhances_edges():
    img = np.full((100, 100, 3), 230, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (80, 80), (40, 40, 40), thickness=5)
    sharpened = sharpen_image(img, intensity=1.5)
    assert sharpened.shape == img.shape
    assert np.any(sharpened != img)

def test_tool_rotate():
    img = np.full((100, 200, 3), 150, dtype=np.uint8)
    rotated_90 = rotate_image(img, angle=90)
    assert rotated_90.shape[0] == 200
    assert rotated_90.shape[1] == 100
    # Auto-detect branch
    rotated_auto = rotate_image(img, angle=0)
    assert rotated_auto is not None

def test_tool_contrast():
    img = np.full((100, 100, 3), 100, dtype=np.uint8)
    contrasted = adjust_contrast(img, alpha=1.5, beta=10)
    assert contrasted.shape == img.shape

def test_tool_blank_page_detection():
    # Pure white image is blank
    blank_img = np.full((200, 200, 3), 255, dtype=np.uint8)
    assert is_page_blank(blank_img) is True
    
    # Image with substantial content is not blank
    content_img = np.full((200, 200, 3), 255, dtype=np.uint8)
    cv2.rectangle(content_img, (20, 20), (180, 180), (0, 0, 0), -1)
    assert is_page_blank(content_img) is False

def test_tool_duplicate_detection():
    doc = fitz.open()
    # Add page 1 and duplicate page 2
    for _ in range(2):
        p = doc.new_page(width=300, height=400)
        p.insert_text((50, 50), "IDENTICAL PAGE CONTENT", fontsize=14)
    # Add distinct page 3
    p3 = doc.new_page(width=300, height=400)
    p3.insert_text((50, 50), "COMPLETELY DIFFERENT CONTENT TEXT", fontsize=14)
    p_bytes = doc.tobytes()
    doc.close()

    duplicates = detect_duplicate_pages(p_bytes)
    assert len(duplicates) == 1
    assert 1 in duplicates[0]["pages"]
    assert 2 in duplicates[0]["pages"]

def test_tool_render_pdf():
    pdf_bytes = create_test_pdf_bytes(2)
    zip_bytes, count = render_pdf_to_png_zip(pdf_bytes, dpi=72)
    assert count == 2
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        assert len(z.namelist()) == 2
        assert "page_001.png" in z.namelist()

# ==========================================
# 5. CORRECTIONS & CONSENT TESTS
# ==========================================

def test_silent_correction_logging_and_consent(monkeypatch, tmp_path):
    monkeypatch.setattr(correction_store, "CORRECTIONS_FILE", tmp_path / "corrections.jsonl")
    monkeypatch.setattr(correction_store, "CONSENT_FILE", tmp_path / "consent_settings.json")

    # Enable consent
    set_correction_consent(True)
    assert get_correction_consent() is True

    res = log_correction(
        original_text="Misspeled text",
        corrected_text="Misspelled text",
        page=1,
        bbox=[40, 50, 200, 80],
        extractor="Tesseract OCR",
        confidence=0.65
    )
    assert res["status"] == "logged"
    assert res["record"]["corrected_text"] == "Misspelled text"

    # Disable consent
    set_correction_consent(False)
    res_opt_out = log_correction(
        original_text="Before",
        corrected_text="After",
        page=1,
        bbox=[],
        extractor="Tesseract OCR",
        confidence=0.5
    )
    assert res_opt_out["status"] == "skipped"
    # Restore consent
    set_correction_consent(True)

# ==========================================
# 6. FASTAPI INTEGRATION ENDPOINTS TESTS
# ==========================================

def test_api_validate_endpoint():
    pdf_bytes = create_test_pdf_bytes(1)
    response = client.post(
        "/api/validate",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["banner_message"] == "Your uploaded file is valid."

def test_api_parse_and_export_flow(monkeypatch, tmp_path):
    monkeypatch.setattr(audit_store, "AUDIT_LOG_FILE", tmp_path / "audit.jsonl")
    pdf_bytes = create_test_pdf_bytes(1)
    
    # 1. Parse endpoint
    parse_resp = client.post(
        "/api/parse",
        files={"file": ("sample_job.pdf", pdf_bytes, "application/pdf")}
    )
    assert parse_resp.status_code == 200
    job_info = parse_resp.json()
    job_id = job_info["job_id"]
    assert job_id is not None
    assert job_info["status"] == "processing"

    # 2. Check settings endpoints
    consent_resp = client.get("/api/settings/consent")
    assert consent_resp.status_code == 200
    assert "consent_enabled" in consent_resp.json()

    pii_resp = client.get("/api/settings/pii")
    assert pii_resp.status_code == 200
    assert "pii_redaction" in pii_resp.json()
    delete_resp = client.delete(f"/api/jobs/{job_id}")
    assert delete_resp.status_code == 200

def test_api_image_tools_endpoints():
    img_bytes = create_test_image_bytes(200, 200)

    # Deskew endpoint
    res_deskew = client.post("/api/tools/deskew", files={"file": ("test.png", img_bytes, "image/png")})
    assert res_deskew.status_code == 200
    assert res_deskew.headers["content-type"] == "image/png"

    # Rotate endpoint
    res_rotate = client.post(
        "/api/tools/rotate",
        files={"file": ("test.png", img_bytes, "image/png")},
        data={"angle": 90}
    )
    assert res_rotate.status_code == 200
    assert res_rotate.headers["content-type"] == "image/png"

    # Contrast endpoint
    res_contrast = client.post(
        "/api/tools/contrast",
        files={"file": ("test.png", img_bytes, "image/png")},
        data={"alpha": 1.2, "beta": 5}
    )
    assert res_contrast.status_code == 200
    assert res_contrast.headers["content-type"] == "image/png"

    res_sharpness = client.post(
        "/api/tools/sharpness",
        files={"file": ("test.png", img_bytes, "image/png")},
        data={"intensity": 1.5}
    )
    assert res_sharpness.status_code == 200
    assert res_sharpness.headers["content-type"] == "image/png"
