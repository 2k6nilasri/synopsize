import pymupdf as fitz
import io
import zipfile
from typing import Tuple

def render_pdf_to_png_zip(pdf_bytes: bytes, dpi: int = 150) -> Tuple[bytes, int]:
    """Renders all PDF pages as PNG images at specified DPI and returns a zip archive."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            zip_file.writestr(f"page_{i+1:03d}.png", img_bytes)
            
    page_count = len(doc)
    doc.close()
    return zip_buffer.getvalue(), page_count
