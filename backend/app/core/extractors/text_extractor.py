import base64
import binascii
import hashlib
import io
import re
from email import policy
from email.generator import BytesGenerator
from email.parser import BytesParser
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional

from app.config import MAX_ATTACHMENT_BYTES, MAX_ATTACHMENT_DEPTH
from striprtf.striprtf import rtf_to_text


AttachmentParser = Callable[[bytes, str, int, List[int]], Dict[str, Any]]


class _HTMLDocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: List[Dict[str, str]] = []
        self.text: List[str] = []
        self.table_rows: List[List[str]] = []
        self.table_row: List[str] = []
        self.cell_text: List[str] = []
        self.skip_depth = 0
        self.in_table = False
        self.in_cell = False
        self.current_kind = "paragraph"

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "table":
            self._flush_text()
            self.in_table = True
            self.table_rows = []
        elif tag == "tr" and self.in_table:
            self.table_row = []
        elif tag in {"th", "td"} and self.in_table:
            self.in_cell = True
            self.cell_text = []
        elif tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            self._flush_text()
            self.current_kind = "heading"
        elif tag == "li":
            self._flush_text()
            self.current_kind = "list"
        elif tag == "br":
            self._flush_text()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in {"th", "td"} and self.in_table:
            self.table_row.append(" ".join("".join(self.cell_text).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_table and self.table_row:
            self.table_rows.append(self.table_row)
        elif tag == "table" and self.in_table:
            self.in_table = False
            if self.table_rows:
                self.blocks.append({"type": "table", "content": _rows_to_markdown(self.table_rows)})
        elif tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush_text()
            self.current_kind = "paragraph"

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.in_table:
            if self.in_cell:
                self.cell_text.append(data)
        else:
            self.text.append(data)

    def _flush_text(self) -> None:
        content = " ".join(" ".join(self.text).split())
        if content:
            self.blocks.append({"type": self.current_kind, "content": content})
        self.text = []

    def finish(self) -> List[Dict[str, str]]:
        self._flush_text()
        return self.blocks


def _rows_to_markdown(rows: List[List[str]]) -> str:
    width = max((len(row) for row in rows), default=0)
    if not width:
        return ""
    normalized = [row + [""] * (width - len(row)) for row in rows]
    return "\n".join(
        "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |"
        for row in [normalized[0], ["---"] * width, *normalized[1:]]
    )


def _preview(page_number: int, label: str) -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000">'
        '<rect width="100%" height="100%" fill="#f8fafc"/>'
        f'<text x="50%" y="48%" text-anchor="middle" font-family="sans-serif" '
        f'font-size="24" fill="#475569">{label} - page {page_number}</text></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _make_document(
    filename: str, sections: List[Dict[str, str]], ocr_label: str
) -> Dict[str, Any]:
    blocks: List[Dict[str, Any]] = []
    ocr_lines = [f"--- {ocr_label} ---"]
    for index, section in enumerate(sections, start=1):
        content = section["content"].strip()
        if not content:
            continue
        block_type = section["type"]
        confidence = 0.97 if block_type == "table" else 0.99
        blocks.append(
            {
                "id": f"block-1-{len(blocks) + 1}",
                "type": block_type,
                "reading_order": len(blocks) + 1,
                "page": 1,
                "bbox": [40, 35 + index * 35, 760, 65 + index * 35],
                "content": content,
                "confidence": confidence,
                "extractor": f"{ocr_label} parser",
                "source_reference": f"{ocr_label.lower().replace(' ', '_')}_{index}",
            }
        )
        ocr_lines.append(f"Line {index} [{confidence:.2f}]: {content}")
    return {
        "total_pages": 1,
        "pages": [
            {
                "page_number": 1,
                "width": 800,
                "height": 1000,
                "image_data": _preview(1, filename),
                "blocks": blocks,
            }
        ],
        "ocr_text": "\n".join(ocr_lines),
    }


def _html_sections(text: str) -> List[Dict[str, str]]:
    parser = _HTMLDocumentParser()
    parser.feed(text)
    return parser.finish()


def process_text_document(
    file_bytes: bytes,
    filename: str,
    *,
    attachment_parser: Optional[AttachmentParser] = None,
    attachment_depth: int = 0,
    attachment_state: Optional[List[int]] = None,
) -> Dict[str, Any]:
    extension = filename.rsplit(".", 1)[-1].lower()
    text = file_bytes.decode("utf-8-sig", errors="replace")
    child_documents: List[Dict[str, Any]] = []

    if extension in {"html", "htm"}:
        sections = _html_sections(text)
    elif extension == "rtf":
        sections = [
            {"type": "paragraph", "content": line.strip()}
            for line in rtf_to_text(text).splitlines()
            if line.strip()
        ]
    elif extension in {"eml", "msg"}:
        if extension == "msg":
            sections, child_documents = _process_msg(
                file_bytes,
                filename,
                attachment_parser,
                attachment_depth,
                attachment_state or [0],
            )
        else:
            sections, child_documents = _process_eml(
                file_bytes,
                attachment_parser,
                attachment_depth,
                attachment_state or [0],
            )
    else:
        sections = []
        for line in text.splitlines():
            content = line.strip()
            if not content:
                continue
            if extension == "md" and content.startswith("#"):
                block_type = "heading"
                content = content.lstrip("#").strip()
            elif extension == "md" and re.match(r"^[-*+]\s+", content):
                block_type = "list"
            elif extension == "md" and content.startswith("```"):
                block_type = "code"
            else:
                block_type = "paragraph"
            sections.append({"type": block_type, "content": content})

    result = _make_document(filename, sections, extension.upper())
    if child_documents:
        result["child_documents"] = child_documents
    return result


def _process_eml(
    file_bytes: bytes,
    attachment_parser: Optional[AttachmentParser],
    depth: int,
    attachment_state: List[int],
) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    message = BytesParser(policy=policy.default).parsebytes(file_bytes)
    sections: List[Dict[str, str]] = []
    for header in ("From", "To", "Cc", "Date", "Subject"):
        value = message.get(header)
        if value:
            sections.append({"type": "paragraph", "content": f"{header}: {value}"})

    plain_parts: List[str] = []
    html_parts: List[str] = []
    attachments: List[tuple[str, bytes]] = []

    def collect_parts(part: Any) -> None:
        content_type = part.get_content_type()
        filename = part.get_filename()
        if content_type == "message/rfc822":
            nested_messages = part.get_payload()
            decoded_payload = part.get_payload(decode=True)
            if decoded_payload:
                attachments.append(
                    (filename or "attached-message.eml", decoded_payload)
                )
            elif isinstance(nested_messages, list) and nested_messages:
                nested_message = nested_messages[0]
                buffer = io.BytesIO()
                if nested_message.items():
                    BytesGenerator(buffer, policy=policy.default).flatten(nested_message)
                else:
                    nested_payload = nested_message.get_payload(decode=True)
                    if nested_payload is None:
                        nested_payload = nested_message.get_payload()
                    if isinstance(nested_payload, (str, bytes)):
                        encoded_payload = (
                            nested_payload.encode("ascii", errors="ignore")
                            if isinstance(nested_payload, str)
                            else nested_payload
                        )
                        try:
                            decoded_message = base64.b64decode(
                                b"".join(encoded_payload.split()), validate=True
                            )
                        except binascii.Error:
                            decoded_message = b""
                        if decoded_message.lower().startswith(
                            (b"subject:", b"from:", b"to:", b"mime-version:")
                        ):
                            nested_payload = decoded_message
                        elif isinstance(nested_payload, str):
                            nested_payload = nested_payload.encode("utf-8")
                    if isinstance(nested_payload, bytes):
                        buffer.write(nested_payload)
                attachments.append(
                    (filename or "attached-message.eml", buffer.getvalue())
                )
            return
        if filename:
            attachments.append((filename, part.get_payload(decode=True) or b""))
            return
        if part.is_multipart():
            for child_part in part.iter_parts():
                collect_parts(child_part)
        elif content_type == "text/plain":
            plain_parts.append(part.get_content())
        elif content_type == "text/html":
            html_parts.append(part.get_content())

    collect_parts(message)

    body_text = "\n".join(plain_parts).strip()
    body_sections = (
        [{"type": "paragraph", "content": line.strip()} for line in body_text.splitlines() if line.strip()]
        if body_text
        else _html_sections("\n".join(html_parts))
    )
    sections.extend(body_sections)

    child_documents = []
    for name, payload in attachments:
        if not payload:
            continue
        child = _parse_attachment(
            name, payload, attachment_parser, depth, attachment_state
        )
        if child is not None:
            child_documents.append(child)
    return sections, child_documents


def _process_msg(
    file_bytes: bytes,
    filename: str,
    attachment_parser: Optional[AttachmentParser],
    depth: int,
    attachment_state: List[int],
) -> tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    import extract_msg
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "message.msg"
        path.write_bytes(file_bytes)
        message = extract_msg.Message(str(path))
        sections = [
            {"type": "paragraph", "content": f"{label}: {value}"}
            for label, value in (
                ("From", message.sender),
                ("To", message.to),
                ("Date", message.date),
                ("Subject", message.subject),
            )
            if value
        ]
        if message.body:
            sections.extend(
                {"type": "paragraph", "content": line.strip()}
                for line in message.body.splitlines()
                if line.strip()
            )
        elif message.htmlBody:
            html_body = message.htmlBody
            if isinstance(html_body, bytes):
                html_body = html_body.decode("utf-8", errors="replace")
            sections.extend(_html_sections(html_body))
        children = []
        for attachment in message.attachments:
            payload = getattr(attachment, "data", None)
            name = getattr(attachment, "longFilename", None) or getattr(
                attachment, "shortFilename", None
            )
            if isinstance(payload, extract_msg.MSGFile):
                payload = payload.exportBytes()
                if name and not name.lower().endswith(".msg"):
                    name += ".msg"
            if isinstance(payload, bytes) and name:
                child = _parse_attachment(
                    name, payload, attachment_parser, depth, attachment_state
                )
                if child is not None:
                    children.append(child)
        message.close()
        return sections, children


def _parse_attachment(
    filename: str,
    payload: bytes,
    attachment_parser: Optional[AttachmentParser],
    depth: int,
    attachment_state: List[int],
) -> Optional[Dict[str, Any]]:
    if attachment_parser is None:
        return {
            "filename": filename,
            "status": "not_parsed",
            "file_size": len(payload),
        }
    if depth >= MAX_ATTACHMENT_DEPTH:
        return {"filename": filename, "status": "depth_limit", "file_size": len(payload)}
    if attachment_state[0] + len(payload) > MAX_ATTACHMENT_BYTES:
        return {"filename": filename, "status": "size_limit", "file_size": len(payload)}

    attachment_state[0] += len(payload)
    child = attachment_parser(payload, filename, depth + 1, attachment_state)
    child["filename"] = filename
    child["file_size"] = len(payload)
    child["file_sha256"] = hashlib.sha256(payload).hexdigest()
    child["parent_id"] = None
    return child
