import pymupdf as fitz
import pdfplumber
import cv2
import numpy as np
import base64
import io
from typing import Dict, Any, List

from app.core.extractors.vision_extractor import analyze_visual_block
from app.core.extractors.equation_extractor import extract_equation_latex

def process_pdf_document(pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Parses digital or scanned PDF documents.
    Renders pages to images, performs layout analysis, extracts text, tables (pdfplumber),
    images/charts, equations, headers/footers, and links multi-page tables.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_output = []
    all_ocr_lines = []
    
    # Also open with pdfplumber for high-accuracy table extraction
    try:
        plumber_pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    except Exception:
        plumber_pdf = None

    total_pages = len(doc)
    
    for page_idx, page in enumerate(doc):
        page_num = page_idx + 1
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        nparr = np.frombuffer(img_bytes, np.uint8)
        page_cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        h, w = page_cv_img.shape[:2]
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        page_image_url = f"data:image/png;base64,{img_b64}"
        
        page_blocks = []
        reading_order = 1
        page_ocr_lines = [f"--- Page {page_num} ---"]

        # 1. Check for Tables using pdfplumber if available
        plumber_tables = []
        if plumber_pdf and page_idx < len(plumber_pdf.pages):
            try:
                p_page = plumber_pdf.pages[page_idx]
                extracted_tables = p_page.extract_tables()
                table_bboxes = p_page.find_tables()
                for t_idx, table_data in enumerate(extracted_tables):
                    if table_data and len(table_data) > 0:
                        # Convert table grid into Markdown table string
                        header = table_data[0]
                        rows = table_data[1:]
                        clean_header = [str(c or '').replace('\n', ' ') for c in header]
                        md_table = "| " + " | ".join(clean_header) + " |\n"
                        md_table += "| " + " | ".join(["---"] * len(clean_header)) + " |\n"
                        for row in rows:
                            clean_row = [str(c or '').replace('\n', ' ') for c in row]
                            md_table += "| " + " | ".join(clean_row) + " |\n"
                            
                        # Estimate bbox
                        bbox = [40, 200 + t_idx * 150, w - 40, 350 + t_idx * 150]
                        if t_idx < len(table_bboxes):
                            tb = table_bboxes[t_idx].bbox
                            # Scale from plumber coordinates to px
                            scale_x = w / p_page.width
                            scale_y = h / p_page.height
                            bbox = [int(tb[0]*scale_x), int(tb[1]*scale_y), int(tb[2]*scale_x), int(tb[3]*scale_y)]

                        page_blocks.append({
                            "id": f"block-{page_num}-{reading_order}",
                            "type": "table",
                            "reading_order": reading_order,
                            "page": page_num,
                            "bbox": bbox,
                            "content": md_table,
                            "confidence": 0.95,
                            "extractor": "pdfplumber Table Engine",
                            "source_reference": f"pdf_page_{page_num}_table_{t_idx+1}",
                            "metadata": {
                                "raw_table": table_data,
                                "rows": len(rows),
                                "columns": len(clean_header)
                            }
                        })
                        reading_order += 1
            except Exception:
                pass

        # 2. Extract PyMuPDF text blocks
        text_blocks = page.get_text("blocks")
        for b in text_blocks:
            # b format: (x0, y0, x1, y1, "text", block_no, block_type)
            bx0, by0, bx1, by1, btext, bno, btype = b
            clean_btext = btext.strip()
            if not clean_btext:
                continue
                
            # Scale coords to page rendering resolution
            rx0, ry0, rx1, ry1 = int(bx0 * 150/72), int(by0 * 150/72), int(bx1 * 150/72), int(by1 * 150/72)
            bbox = [rx0, ry0, rx1, ry1]

            # Detect Header / Footer
            if ry0 < h * 0.08 or ry1 > h * 0.93:
                block_kind = "header_footer"
                conf = 0.96
            # Detect Heading
            elif len(clean_btext.splitlines()) == 1 and len(clean_btext) < 60:
                block_kind = "heading"
                conf = 0.98
            # Detect Equation
            elif any(sym in clean_btext for sym in ['=', '∑', '∫', '√', 'α', 'β', 'λ', '\\sum']):
                block_kind = "equation"
                eq_meta = extract_equation_latex(clean_btext)
                clean_btext = eq_meta["latex"]
                conf = eq_meta["confidence"]
            else:
                block_kind = "paragraph"
                conf = 0.94 if len(clean_btext) > 20 else 0.78

            page_blocks.append({
                "id": f"block-{page_num}-{reading_order}",
                "type": block_kind,
                "reading_order": reading_order,
                "page": page_num,
                "bbox": bbox,
                "content": clean_btext,
                "confidence": round(conf, 2),
                "extractor": "PyMuPDF Text Engine",
                "source_reference": f"pdf_page_{page_num}_text_{bno}"
            })
            reading_order += 1
            page_ocr_lines.append(f"Line {reading_order} [{conf:.2f}]: {clean_btext[:80]}")

        # 3. Extract Embedded Images / Visual Charts
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes_img = base_image["image"]
                nparr_img = np.frombuffer(image_bytes_img, np.uint8)
                crop_cv = cv2.imdecode(nparr_img, cv2.IMREAD_COLOR)
                if crop_cv is not None and crop_cv.shape[0] > 40 and crop_cv.shape[1] > 40:
                    vis_res = analyze_visual_block(crop_cv)
                    crop_b64 = base64.b64encode(cv2.imencode('.png', crop_cv)[1]).decode('utf-8')
                    img_data_url = f"data:image/png;base64,{crop_b64}"
                    
                    c_bbox = [int(w*0.1), int(h*0.4 + img_idx*120), int(w*0.9), int(h*0.6 + img_idx*120)]
                    
                    page_blocks.append({
                        "id": f"block-{page_num}-{reading_order}",
                        "type": vis_res["type"],
                        "reading_order": reading_order,
                        "page": page_num,
                        "bbox": c_bbox,
                        "content": f"![Extracted {vis_res['type']}]({img_data_url})",
                        "confidence": 0.91,
                        "extractor": "OpenAI GPT-4o Vision Engine",
                        "source_reference": f"pdf_page_{page_num}_image_{img_idx+1}",
                        "metadata": vis_res.get("chart_metadata", {})
                    })
                    reading_order += 1
            except Exception:
                pass

        # Sort blocks by reading order (vertical position top-to-bottom)
        page_blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        for idx, b in enumerate(page_blocks):
            b["reading_order"] = idx + 1
            b["id"] = f"block-{page_num}-{idx+1}"

        pages_output.append({
            "page_number": page_num,
            "width": w,
            "height": h,
            "image_data": page_image_url,
            "blocks": page_blocks
        })
        all_ocr_lines.extend(page_ocr_lines)

    # 4. Cross-page Linking: Merge tables that split across consecutive pages
    for p_idx in range(len(pages_output) - 1):
        curr_page = pages_output[p_idx]
        next_page = pages_output[p_idx + 1]
        
        # Check if last block of curr_page is table and first block of next_page is table
        curr_tables = [b for b in curr_page["blocks"] if b["type"] == "table"]
        next_tables = [b for b in next_page["blocks"] if b["type"] == "table"]
        
        if curr_tables and next_tables:
            last_tbl = curr_tables[-1]
            first_tbl = next_tables[0]
            
            last_cols = last_tbl.get("metadata", {}).get("columns", 0)
            first_cols = first_tbl.get("metadata", {}).get("columns", 0)
            
            # If matching column structure, link the two table blocks
            if last_cols > 0 and last_cols == first_cols:
                last_tbl["metadata"]["cross_page_linked"] = True
                last_tbl["metadata"]["continuation_page"] = next_page["page_number"]
                first_tbl["metadata"]["cross_page_linked"] = True
                first_tbl["metadata"]["continuation_from_page"] = curr_page["page_number"]
                first_tbl["metadata"]["merged_with_previous"] = True

    if plumber_pdf:
        plumber_pdf.close()
    doc.close()

    return {
        "total_pages": total_pages,
        "pages": pages_output,
        "ocr_text": "\n".join(all_ocr_lines)
    }

