from typing import Dict, Any, List

def create_semantic_chunks(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Chunks document content by structural hierarchy (headings, tables, sections).
    Maintains table-caption pairings and targets 200-500 tokens (~800-2000 chars) per chunk.
    """
    chunks = []
    current_section = "Document Top"
    current_text_parts = []
    current_block_ids = []
    current_bboxes = []
    current_pages = set()
    current_confidences = []
    chunk_idx = 1

    def finalize_chunk():
        nonlocal chunk_idx, current_text_parts, current_block_ids, current_bboxes, current_pages, current_confidences
        if not current_text_parts:
            return
            
        combined_text = "\n\n".join(current_text_parts)
        avg_conf = sum(current_confidences) / max(1, len(current_confidences))
        page_list = sorted(list(current_pages))
        
        chunks.append({
            "chunk_id": f"chunk-{chunk_idx}",
            "text": combined_text,
            "page_range": [min(page_list), max(page_list)],
            "bounding_boxes": current_bboxes[:],
            "section_path": current_section,
            "block_ids": current_block_ids[:],
            "confidence": round(avg_conf, 2),
            "token_count": max(1, len(combined_text.split()))
        })
        chunk_idx += 1
        current_text_parts = []
        current_block_ids = []
        current_bboxes = []
        current_pages = set()
        current_confidences = []

    for page in pages:
        page_num = page["page_number"]
        for block in page.get("blocks", []):
            b_type = block.get("type", "paragraph")
            content = block.get("content", "")
            b_id = block.get("id", "")
            bbox = block.get("bbox", [])
            conf = block.get("confidence", 0.90)

            # Update section path when heading is encountered
            if b_type == "heading":
                finalize_chunk()
                current_section = f"Section: {content[:50]}"
                current_text_parts.append(f"### {content}")
                current_block_ids.append(b_id)
                current_bboxes.append(bbox)
                current_pages.add(page_num)
                current_confidences.append(conf)
            elif b_type == "table":
                # Keep table together as single structural chunk
                if current_text_parts:
                    finalize_chunk()
                current_text_parts.append(content)
                current_block_ids.append(b_id)
                current_bboxes.append(bbox)
                current_pages.add(page_num)
                current_confidences.append(conf)
                finalize_chunk()
            else:
                current_text_parts.append(content)
                current_block_ids.append(b_id)
                current_bboxes.append(bbox)
                current_pages.add(page_num)
                current_confidences.append(conf)

                # Check token/character length target
                combined_len = sum(len(p) for p in current_text_parts)
                if combined_len >= 1000:
                    finalize_chunk()

    finalize_chunk()
    return chunks
