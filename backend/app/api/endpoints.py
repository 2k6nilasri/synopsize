import asyncio
import io
import json
import zipfile
import logging
import shutil
import uuid
import cv2
import numpy as np

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Response
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.config import (
    CORRECTIONS_DIR,
    JOBS_DIR,
    MAX_FILE_SIZE_BYTES,
    SETTINGS,
    TOOLS_DIR,
    UPLOADS_DIR,
)
from app.core.security import validate_uploaded_file, mask_pii_entities
from app.core.pipeline import run_pipeline_job, JOB_STORES, JOB_EVENTS, get_job_file_path, STAGES
from app.core.corrections import log_correction, get_correction_consent, set_correction_consent
from app.core.semantic.indexer import VectorIndex
from app.core.audit import audit_csv, read_audit_log, verify_audit_log

# Import Image Tools
from app.core.tools.deskew import deskew_image
from app.core.tools.denoise import denoise_image
from app.core.tools.sharpen import sharpen_image
from app.core.tools.rotate import rotate_image
from app.core.tools.contrast import adjust_contrast
from app.core.tools.blank_detect import is_page_blank, detect_blank_pages_pdf
from app.core.tools.duplicate_detect import detect_duplicate_pages
from app.core.tools.render_pdf import render_pdf_to_png_zip

router = APIRouter()
logger = logging.getLogger(__name__)


async def _read_upload(file: UploadFile) -> bytes:
    file_bytes = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Upload exceeds the {MAX_FILE_SIZE_BYTES}-byte limit.",
        )
    return file_bytes


def _normalized_job_id(job_id: str) -> str:
    try:
        return str(uuid.UUID(job_id))
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid job ID.") from error


@router.get("/audit")
async def get_audit_log(format: str = "json"):
    """Returns the hash-chain verification result and audit entries."""
    try:
        records = read_audit_log()
        valid, verified_count = verify_audit_log(records)
    except (OSError, json.JSONDecodeError) as error:
        logger.exception("Could not read the audit log.")
        return JSONResponse(
            status_code=500,
            content={
                "integrity_valid": False,
                "error": f"Audit log could not be read: {error}",
            },
        )
    if format == "csv":
        return Response(
            content=audit_csv(records),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=synopsize-audit.csv"},
        )
    if format != "json":
        raise HTTPException(status_code=400, detail="Invalid audit format requested")
    return {
        "integrity_valid": valid,
        "verified_entries": verified_count,
        "records": records,
    }


@router.post("/validate")
async def validate_file_endpoint(file: UploadFile = File(...)):
    """Validates uploaded file against 5 security & integrity checks."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    return report

@router.post("/parse")
async def start_parse_job(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Validates and launches an asynchronous 7-stage document parsing job."""
    file_bytes = await _read_upload(file)
    filename = file.filename or "upload"
    report = validate_uploaded_file(file_bytes, filename)
    
    if not report["is_valid"]:
        messages = " ".join(check["message"] for check in report["checks"]).lower()
        if "unsupported file extension" in messages:
            code = "UNSUPPORTED_FORMAT"
        elif "encrypted" in messages or "password-protected" in messages:
            code = "ENCRYPTED"
        elif "corrupt" in messages or "integrity" in messages:
            code = "CORRUPT"
        else:
            code = "INVALID_FILE"
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "stage": 2,
                "stage_name": "File Validation",
                "code": code,
                "message": report["banner_message"],
                "recoverable": False,
                "checks": report["checks"],
            },
        )

    job_id = report["file_id"]
    saved_path = report["saved_path"]

    # Initialize job state
    JOB_STORES[job_id] = {
        "status": "processing",
        "filename": filename,
        "current_stage": 1,
        "stage_statuses": {i: "pending" for i in range(1, 8)}
    }

    # Run pipeline in background task
    background_tasks.add_task(run_pipeline_job, job_id, saved_path, filename)

    return {
        "job_id": job_id,
        "filename": filename,
        "status": "processing",
        "validation_report": report
    }

@router.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str):
    """Server-Sent Events (SSE) stream for real-time pipeline stage progress."""
    job_id = _normalized_job_id(job_id)
    if (
        job_id not in JOB_STORES
        and job_id not in JOB_EVENTS
        and not get_job_file_path(job_id).exists()
    ):
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        sent_count = 0
        while True:
            events = JOB_EVENTS.get(job_id, [])
            while sent_count < len(events):
                evt = events[sent_count]
                sent_count += 1
                yield f"data: {json.dumps(evt)}\n\n"
            
            job_state = JOB_STORES.get(job_id)
            if job_state and job_state.get("status") in ["completed", "failed"]:
                yield f"data: {json.dumps({'status': job_state['status'], 'done': True})}\n\n"
                break
                
            await asyncio.sleep(0.2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Returns structured document output (Markdown, JSON, OCR text, pages, chunks)."""
    job_id = _normalized_job_id(job_id)

    # Check disk cache first
    job_file = get_job_file_path(job_id)
    if job_file.exists():
        with open(job_file, "r", encoding="utf-8") as f:
            return json.load(f)

    job_state = JOB_STORES.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_state["status"] == "processing":
        return {"job_id": job_id, "status": "processing", "current_stage": job_state.get("current_stage", 1)}
    elif job_state["status"] == "failed":
        return JSONResponse(status_code=500, content=job_state.get("error", {
            "status": "error",
            "stage": job_state.get("current_stage", 1),
            "stage_name": "Document Processing",
            "code": "PROCESSING_FAILED",
            "message": "Processing failed.",
            "recoverable": False,
        }))

    return job_state.get("result", {})

@router.get("/jobs/{job_id}/export")
async def export_job_result(job_id: str, format: str = "zip"):
    """Exports structured output as Markdown (.md), JSON (.json), OCR Text (.txt), or ZIP archive."""
    job_id = _normalized_job_id(job_id)
    job_file = get_job_file_path(job_id)
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job result not found")

    with open(job_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    filename_base = Path(data.get("filename", "document")).stem

    md_content = data.get("markdown", "")
    ocr_content = data.get("ocr_text", "")
    json_data = data

    if get_pii_enabled():
        md_content = mask_pii_entities(md_content)
        ocr_content = mask_pii_entities(ocr_content)
        # Deep mask json string representation
        json_str = mask_pii_entities(json.dumps(data, indent=2))
        try:
            json_data = json.loads(json_str)
        except Exception:
            pass

    if format == "md":
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename_base}_synopsize.md"}
        )
    elif format == "json":
        return Response(
            content=json.dumps(json_data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename_base}_synopsize.json"}
        )
    elif format == "txt":
        return Response(
            content=ocr_content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename_base}_synopsize_ocr.txt"}
        )
    elif format == "zip":
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{filename_base}_synopsize.md", md_content)
            z.writestr(f"{filename_base}_synopsize.json", json.dumps(json_data, indent=2))
            z.writestr(f"{filename_base}_synopsize_ocr.txt", ocr_content)
            z.writestr(f"{filename_base}_chunks.jsonl", "\n".join(json.dumps(c) for c in data.get("chunks", [])))

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename_base}_export.zip"}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format requested")

@router.delete("/jobs/{job_id}")
async def delete_job_data(job_id: str):
    """Deletes uploaded file and processed job results immediately ('Delete my data now')."""
    job_id = _normalized_job_id(job_id)
    job_file = get_job_file_path(job_id)
    upload_dir = UPLOADS_DIR / job_id
    if (
        not job_file.exists()
        and not upload_dir.exists()
        and job_id not in JOB_STORES
        and job_id not in JOB_EVENTS
    ):
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        if job_file.exists():
            job_file.unlink()
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
    except OSError as error:
        logger.exception("Could not delete data for job %s.", job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Could not delete all data for job {job_id}.",
        ) from error

    if job_id in JOB_STORES:
        del JOB_STORES[job_id]
    if job_id in JOB_EVENTS:
        del JOB_EVENTS[job_id]

    return {"status": "success", "message": f"All data for job {job_id} deleted permanently."}

@router.post("/search")
async def semantic_search(job_id: str = Form(...), query: str = Form(...)):
    """Runs semantic vector search over a document's structural chunks."""
    job_id = _normalized_job_id(job_id)
    if not SETTINGS["processing"]["embeddings_enabled"]:
        raise HTTPException(status_code=503, detail="Semantic indexing is disabled by configuration.")
    job_file = get_job_file_path(job_id)
    if not job_file.exists():
        raise HTTPException(status_code=404, detail="Job not found")

    with open(job_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    indexer = VectorIndex(chunks)
    matched_chunks = indexer.search(query, top_k=5)
    return {"query": query, "results": matched_chunks}

@router.post("/corrections")
async def save_correction(
    original_text: str = Form(...),
    corrected_text: str = Form(...),
    page: int = Form(...),
    extractor: str = Form(...),
    confidence: float = Form(...),
    bbox_json: str = Form("[]"),
    cropped_image_base64: Optional[str] = Form(None)
):
    """Silently logs low-confidence block edits for future fine-tuning."""
    try:
        bbox = json.loads(bbox_json)
    except Exception:
        bbox = []
        
    res = log_correction(
        original_text=original_text,
        corrected_text=corrected_text,
        page=page,
        bbox=bbox,
        extractor=extractor,
        confidence=confidence,
        cropped_image_base64=cropped_image_base64
    )
    return res

@router.get("/settings/consent")
async def get_consent():
    """Gets correction logging consent status."""
    return {"consent_enabled": get_correction_consent()}

@router.post("/settings/consent")
async def update_consent(enabled: bool = Form(...)):
    """Updates correction logging consent preference."""
    set_correction_consent(enabled)
    return {"consent_enabled": enabled}

PII_SETTINGS_FILE = CORRECTIONS_DIR / "pii_settings.json"

def get_pii_enabled() -> bool:
    if PII_SETTINGS_FILE.exists():
        try:
            with open(PII_SETTINGS_FILE, "r") as f:
                return json.load(f).get("pii_redaction", False)
        except Exception:
            return False
    return False

def set_pii_enabled(enabled: bool):
    with open(PII_SETTINGS_FILE, "w") as f:
        json.dump({"pii_redaction": enabled}, f)

@router.get("/settings/pii")
async def get_pii_setting():
    """Gets PII redaction setting."""
    return {"pii_redaction": get_pii_enabled()}

@router.post("/settings/pii")
async def update_pii_setting(enabled: bool = Form(...)):
    """Updates PII redaction setting."""
    set_pii_enabled(enabled)
    return {"pii_redaction": enabled}


# --- 8 Image Tools Hub Endpoints ---

@router.post("/tools/deskew")
async def tool_deskew(file: UploadFile = File(...)):
    """Deskews document image."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed = deskew_image(img)
    _, buffer = cv2.imencode('.png', processed)
    
    return Response(content=buffer.tobytes(), media_type="image/png")

@router.post("/tools/denoise")
async def tool_denoise(file: UploadFile = File(...), strength: int = Form(10)):
    """Removes noise and background artifacts."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed = denoise_image(img, strength=strength)
    _, buffer = cv2.imencode('.png', processed)
    return Response(content=buffer.tobytes(), media_type="image/png")

@router.post("/tools/upscale")
@router.post("/tools/sharpness")
async def tool_sharpness(
    file: UploadFile = File(...),
    intensity: float = Form(1.5, ge=0.5, le=3.0),
):
    """Improves image edge clarity using unsharp masking without resizing."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed = sharpen_image(img, intensity=intensity)
    _, buffer = cv2.imencode('.png', processed)
    return Response(content=buffer.tobytes(), media_type="image/png")

@router.post("/tools/rotate")
async def tool_rotate(file: UploadFile = File(...), angle: int = Form(90)):
    """Rotates image by 90, 180, 270 degrees or auto-detects if 0."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed = rotate_image(img, angle=angle)
    _, buffer = cv2.imencode('.png', processed)
    return Response(content=buffer.tobytes(), media_type="image/png")

@router.post("/tools/contrast")
async def tool_contrast(file: UploadFile = File(...), alpha: float = Form(1.3), beta: int = Form(10)):
    """Adjusts contrast and brightness."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed = adjust_contrast(img, alpha=alpha, beta=beta)
    _, buffer = cv2.imencode('.png', processed)
    return Response(content=buffer.tobytes(), media_type="image/png")

@router.post("/tools/blank-pages")
async def tool_blank_pages(file: UploadFile = File(...)):
    """Flags blank pages in a PDF document."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    ext = Path(file.filename).suffix.lower()
    if ext == ".pdf":
        results = detect_blank_pages_pdf(file_bytes)
    else:
        nparr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        blank = is_page_blank(img)
        results = [{"page_number": 1, "is_blank": blank}]

    blank_count = sum(1 for r in results if r["is_blank"])
    return {"filename": file.filename, "total_pages": len(results), "blank_count": blank_count, "pages": results}

@router.post("/tools/duplicates")
async def tool_duplicates(file: UploadFile = File(...)):
    """Detects duplicate pages using perceptual hashing."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    groups = detect_duplicate_pages(file_bytes)
    return {"filename": file.filename, "duplicate_groups": groups}

@router.post("/tools/render-pdf")
async def tool_render_pdf(file: UploadFile = File(...), dpi: int = Form(150)):
    """Renders PDF pages as PNG images and packages into ZIP file."""
    file_bytes = await _read_upload(file)
    report = validate_uploaded_file(file_bytes, file.filename or "upload", store=False)
    if not report["is_valid"]:
        raise HTTPException(status_code=400, detail=report["banner_message"])

    zip_data, count = render_pdf_to_png_zip(file_bytes, dpi=dpi)
    filename_base = Path(file.filename).stem
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename_base}_rendered_pngs.zip"}
    )
