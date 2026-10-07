import cv2
import numpy as np
import pymupdf as fitz
from typing import Dict, Any, List

def compute_dhash(img: np.ndarray, hash_size: int = 8) -> int:
    """Computes difference hash (dhash) for an image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

def hamming_distance(h1: int, h2: int) -> int:
    return bin(h1 ^ h2).count('1')

def detect_duplicate_pages(pdf_bytes: bytes, max_distance: int = 5) -> List[Dict[str, Any]]:
    """Detects duplicate or near-duplicate pages in a PDF document using perceptual hashing."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    hashes = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=72)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        h = compute_dhash(img)
        hashes.append((i + 1, h))
    doc.close()
    
    duplicate_groups = []
    visited = set()
    for i in range(len(hashes)):
        p1, h1 = hashes[i]
        if p1 in visited:
            continue
        group = [p1]
        for j in range(i + 1, len(hashes)):
            p2, h2 = hashes[j]
            if p2 not in visited and hamming_distance(h1, h2) <= max_distance:
                group.append(p2)
                visited.add(p2)
        if len(group) > 1:
            duplicate_groups.append(group)
            visited.add(p1)
            
    return [
        {"group_id": idx + 1, "pages": grp}
        for idx, grp in enumerate(duplicate_groups)
    ]
