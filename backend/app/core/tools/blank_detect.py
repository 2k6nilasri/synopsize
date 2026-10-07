import cv2
import numpy as np
from typing import Dict, Any, List
import pymupdf as fitz

def is_page_blank(img: np.ndarray, threshold: float = 0.99) -> bool:
    """Returns True if the image page is essentially blank (white/empty background)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    # Percentage of white/near-white pixels
    white_pixels = np.sum(gray > 240)
    total_pixels = gray.size
    ratio = white_pixels / total_pixels
    
    # Also check variance of Laplacian (edge content)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return bool(ratio >= threshold or variance < 10.0)

def detect_blank_pages_pdf(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Inspects a PDF document and reports blank status per page."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=100)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        
        blank = is_page_blank(img)
        results.append({
            "page_number": i + 1,
            "is_blank": blank,
            "text_length": len(page.get_text())
        })
    doc.close()
    return results
