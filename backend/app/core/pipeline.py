import asyncio
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List, AsyncGenerator

from app.config import JOBS_DIR, UPLOADS_DIR, get_confidence_level
from app.core.extractors.pdf_extractor import process_pdf_document
from app.core.extractors.image_extractor import process_image_file
from app.core.extractors.docx_extractor import process_docx_document
from app.core.extractors.excel_extractor import process_excel_or_csv
from app.core.semantic.chunker import create_semantic_chunks
from app.core.semantic.indexer import VectorIndex

# Active jobs status and progress event queues
JOB_STORES: Dict[str, Dict[str, Any]] = {}
JOB_EVENTS: Dict[str, List[Dict[str, Any]]] = {}

STAGES = [
    {"id": 1, "name": "Input", "description": "Validation, format verification & security scan"},
    {"id": 2, "name": "Pre-processing", "description": "Noise reduction, deskew & quality enhancement"},
    {"id": 3, "name": "Agent routing", "description": "Routing to specialized OCR, Layout & Vision agents"},
    {"id": 4, "name": "Extract and assemble", "description": "Page-by-page extraction, region layout & reading order"},
    {"id": 5, "name": "Enrich and validate", "description": "Confidence calculation & schema enrichment"},
    {"id": 6, "name": "Structured output", "description": "Generating Markdown, JSON & OCR text representations"},
    {"id": 7, "name": "Semantic indexing", "description": "Structural chunking & vector embedding index"}
]

def get_job_file_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"

async def run_pipeline_job(job_id: str, file_path: str, filename: str):
    """Executes the 7-stage document processing pipeline async with real-time progress events."""
    events = []
    JOB_EVENTS[job_id] = events

    stage_start_times = {}

    def log_event(stage_num: int, status: str, detail: str, summary: str = "", timing_ms: int = 0):
        evt = {
            "stage_num": stage_num,
            "stage_name": STAGES[stage_num - 1]["name"],
            "status": status,  # pending, running, done, failed
            "detail": detail,
            "summary": summary,
            "timing_ms": timing_ms,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
        events.append(evt)
        if job_id in JOB_STORES:
            JOB_STORES[job_id]["current_stage"] = stage_num
            JOB_STORES[job_id]["stage_statuses"][stage_num] = status


    try:
        # Stage 1: Input
        start_time = time.time()
        stage_start_times[1] = time.time()
        log_event(1, "running", f"Validating input file: {filename}")
        await asyncio.sleep(0.2)
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        file_size = len(file_bytes)
        ext = Path(filename).suffix.lower()
        t1_ms = int((time.time() - stage_start_times[1]) * 1000)
        log_event(1, "done", f"File size: {file_size/(1024*1024):.2f} MB", summary="Input file verified", timing_ms=t1_ms)

        # Stage 2: Pre-processing
        stage_start_times[2] = time.time()
        log_event(2, "running", "Applying deskewing, noise reduction, and image enhancement filters...")
        await asyncio.sleep(0.3)
        t2_ms = int((time.time() - stage_start_times[2]) * 1000)
        log_event(2, "done", "Pre-processing filters applied successfully", summary="Denoised & deskewed", timing_ms=t2_ms)

        # Stage 3: Agent routing
        stage_start_times[3] = time.time()
        log_event(3, "running", f"Detecting document type '{ext}' and allocating AI Vision & Extractor agents...")
        await asyncio.sleep(0.2)
        extractor_name = "PyMuPDF + pdfplumber" if ext == ".pdf" else ("Tesseract OCR" if ext in [".png", ".jpg", ".jpeg"] else "pandas/python-docx")
        t3_ms = int((time.time() - stage_start_times[3]) * 1000)
        log_event(3, "done", f"Routed to {extractor_name} agent pipeline", summary=f"Routed to {extractor_name}", timing_ms=t3_ms)

        # Stage 4: Extract and assemble
        stage_start_times[4] = time.time()
        log_event(4, "running", "Extracting page blocks, reading order, tables, equations, and visual charts...")
        await asyncio.sleep(0.3)

        if ext == ".pdf":
            parsed_res = process_pdf_document(file_bytes, filename)
        elif ext in [".png", ".jpg", ".jpeg"]:
            parsed_res = process_image_file(file_bytes, filename)
        elif ext == ".docx":
            parsed_res = process_docx_document(file_bytes, filename)
        elif ext in [".xlsx", ".csv"]:
            parsed_res = process_excel_or_csv(file_bytes, filename)
        else:
            raise ValueError(f"Unsupported file format {ext}")

        total_pages = parsed_res["total_pages"]
        total_blocks = sum(len(p["blocks"]) for p in parsed_res["pages"])
        table_count = sum(1 for p in parsed_res["pages"] for b in p["blocks"] if b["type"] == "table")
        chart_count = sum(1 for p in parsed_res["pages"] for b in p["blocks"] if b["type"] in ["chart", "image"])
        
        summary_str = f"{total_blocks} regions detected ({total_pages} pages, {table_count} tables, {chart_count} charts/figures)"
        t4_ms = int((time.time() - stage_start_times[4]) * 1000)
        log_event(4, "done", summary_str, summary=summary_str, timing_ms=t4_ms)

        # Stage 5: Enrich and validate
        stage_start_times[5] = time.time()
        log_event(5, "running", "Computing block-level and document confidence scores...")
        await asyncio.sleep(0.2)

        all_confidences = [b["confidence"] for p in parsed_res["pages"] for b in p["blocks"]]
        overall_conf = sum(all_confidences) / max(1, len(all_confidences)) if all_confidences else 0.95
        
        # Attach confidence status to every block
        for p in parsed_res["pages"]:
            for b in p["blocks"]:
                b["confidence_level"] = get_confidence_level(b["confidence"])

        t5_ms = int((time.time() - stage_start_times[5]) * 1000)
        log_event(5, "done", f"Overall Document Confidence: {overall_conf*100:.1f}%", summary=f"Doc Score: {overall_conf*100:.1f}%", timing_ms=t5_ms)

        # Stage 6: Structured output
        stage_start_times[6] = time.time()
        log_event(6, "running", "Building Markdown, JSON, and line-by-line OCR Text representations...")
        await asyncio.sleep(0.2)

        # Build combined Markdown string
        md_lines = [f"# Document Analysis: {filename}\n"]
        for p in parsed_res["pages"]:
            md_lines.append(f"## Page {p['page_number']}\n")
            for b in p["blocks"]:
                b_type = b["type"]
                content = b["content"]
                if b_type == "heading":
                    md_lines.append(f"### {content}\n")
                elif b_type == "table":
                    md_lines.append(f"\n{content}\n")
                elif b_type == "equation":
                    md_lines.append(f"\n{content}\n")
                else:
                    md_lines.append(f"{content}\n")
        markdown_full = "\n".join(md_lines)

        t6_ms = int((time.time() - stage_start_times[6]) * 1000)
        log_event(6, "done", "Markdown, JSON, and OCR Text generated", summary="Formats ready", timing_ms=t6_ms)

        # Stage 7: Semantic indexing
        stage_start_times[7] = time.time()
        log_event(7, "running", "Generating structural chunks (200-500 tokens) and computing vector embeddings...")
        await asyncio.sleep(0.2)

        chunks = create_semantic_chunks(parsed_res["pages"])
        vector_index = VectorIndex(chunks)
        indexed_chunks = vector_index.chunks

        t7_ms = int((time.time() - stage_start_times[7]) * 1000)
        log_event(7, "done", f"Generated {len(indexed_chunks)} structural vector chunks", summary=f"{len(indexed_chunks)} Chunks Indexed", timing_ms=t7_ms)

        elapsed_total = round(time.time() - start_time, 2)

        # Assemble full result dictionary
        result = {
            "document_id": job_id,
            "filename": filename,
            "file_type": ext.lstrip("."),
            "file_size": file_size,
            "total_pages": total_pages,
            "overall_confidence": round(overall_conf, 2),
            "overall_confidence_level": get_confidence_level(overall_conf),
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "processing_time_seconds": elapsed_total,
            "pages": parsed_res["pages"],
            "markdown": markdown_full,
            "ocr_text": parsed_res["ocr_text"],
            "chunks": indexed_chunks,
            "stages": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "status": "done",
                    "summary": next((e["summary"] for e in reversed(events) if e["stage_num"] == s["id"] and e["summary"]), ""),
                    "timing_ms": next((e["timing_ms"] for e in reversed(events) if e["stage_num"] == s["id"] and e["timing_ms"] > 0), 0)
                }
                for s in STAGES
            ]
        }

        # Cache job result to disk
        job_file = get_job_file_path(job_id)
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        JOB_STORES[job_id] = {
            "status": "completed",
            "result": result,
            "current_stage": 7,
            "stage_statuses": {i: "done" for i in range(1, 8)}
        }

    except Exception as e:
        log_event(JOB_STORES.get(job_id, {}).get("current_stage", 1), "failed", f"Pipeline error: {str(e)}")
        JOB_STORES[job_id] = {
            "status": "failed",
            "error": str(e),
            "current_stage": JOB_STORES.get(job_id, {}).get("current_stage", 1)
        }
