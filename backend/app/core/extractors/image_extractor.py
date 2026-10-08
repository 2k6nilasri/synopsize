import cv2
import numpy as np
import base64
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
import pytesseract

from app.core.tools.deskew import deskew_image
from app.core.tools.denoise import denoise_image


def _configure_tesseract() -> None:
    executable = shutil.which("tesseract")
    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable
        return

    if os.name == "nt":
        for program_directory in (
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
        ):
            if not program_directory:
                continue
            candidate = Path(program_directory) / "Tesseract-OCR" / "tesseract.exe"
            if candidate.is_file():
                pytesseract.pytesseract.tesseract_cmd = str(candidate)
                return


_configure_tesseract()


def process_image_file(image_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Processes single PNG/JPG image file or scanned page.
    Runs pre-processing (deskew, denoise), layout analysis, and OCR extraction.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Failed to decode image bytes.")
        
    h, w = img.shape[:2]
    
    # Pre-processing pipeline stage
    deskewed = deskew_image(img)
    denoised = denoise_image(deskewed)
    
    # Convert image to base64 for preview display
    _, buffer = cv2.imencode('.png', denoised)
    img_b64 = base64.b64encode(buffer).decode('utf-8')
    page_img_url = f"data:image/png;base64,{img_b64}"
    
    blocks = []
    ocr_lines = []
    
    # Try PyTesseract OCR layout analysis
    try:
        data = pytesseract.image_to_data(denoised, output_type=pytesseract.Output.DICT)
        n_boxes = len(data['text'])
        current_block_lines = []
        current_block_conf = []
        block_idx = 1
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = float(data['conf'][i])
            if conf < 0:
                conf = 0.0
            else:
                conf = conf / 100.0  # normalize to 0.0 - 1.0
                
            if text:
                left, top, width, height = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                bbox = [left, top, left + width, top + height]
                ocr_lines.append(f"Line {len(ocr_lines)+1} [{conf:.2f}]: {text}")
                
                # Group text into paragraph blocks
                current_block_lines.append(text)
                current_block_conf.append(conf)
                
                if len(current_block_lines) >= 3 or i == n_boxes - 1:
                    avg_conf = sum(current_block_conf) / max(1, len(current_block_conf))
                    block_text = " ".join(current_block_lines)
                    b_type = "heading" if len(block_text) < 40 and block_idx == 1 else "paragraph"
                    
                    blocks.append({
                        "id": f"block-1-{block_idx}",
                        "type": b_type,
                        "reading_order": block_idx,
                        "page": 1,
                        "bbox": bbox,
                        "content": block_text,
                        "confidence": round(avg_conf, 2),
                        "extractor": "Tesseract OCR",
                        "source_reference": f"image_page_1_block_{block_idx}"
                    })
                    block_idx += 1
                    current_block_lines = []
                    current_block_conf = []
    except Exception as e:
        blocks = [
            {
                "id": "block-1-1",
                "type": "paragraph",
                "reading_order": 1,
                "page": 1,
                "bbox": [0, 0, w, h],
                "content": "",
                "confidence": 0.0,
                "extractor": "Tesseract OCR",
                "source_reference": "image_page_1_ocr_failure",
                "flags": ["needs_review"],
            }
        ]
        ocr_lines = [f"OCR failed for {filename}: {e}"]

    return {
        "total_pages": 1,
        "width": w,
        "height": h,
        "pages": [
            {
                "page_number": 1,
                "width": w,
                "height": h,
                "image_data": page_img_url,
                "blocks": blocks
            }
        ],
        "ocr_text": "Page 1:\n" + "\n".join(ocr_lines)
    }
