"""Xử lý file upload: ảnh, PDF, Excel → nội dung để gửi Claude API."""

from __future__ import annotations
import base64
import io


SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
SUPPORTED_PDF_TYPES = {"application/pdf"}
SUPPORTED_EXCEL_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
}


def get_file_type(file_name: str, mime_type: str) -> str:
    """Trả về 'image' | 'pdf' | 'excel' | 'unknown'."""
    ext = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    if mime_type in SUPPORTED_IMAGE_TYPES or ext in ("jpg", "jpeg", "png", "gif", "webp"):
        return "image"
    if mime_type in SUPPORTED_PDF_TYPES or ext == "pdf":
        return "pdf"
    if mime_type in SUPPORTED_EXCEL_TYPES or ext in ("xlsx", "xls", "csv"):
        return "excel"
    return "unknown"


def process_image(file_bytes: bytes, mime_type: str) -> dict:
    """Trả về content block dạng image cho Claude API."""
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        mime_type = "image/jpeg"
    b64 = base64.standard_b64encode(file_bytes).decode("ascii")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime_type,
            "data": b64,
        },
    }


def process_pdf(file_bytes: bytes) -> str:
    """Trích xuất text từ PDF. Trả về chuỗi text."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = []
            for i, page in enumerate(pdf.pages[:20], 1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"--- Trang {i} ---\n{text.strip()}")
            return "\n\n".join(pages) if pages else "[PDF không trích xuất được text]"
    except ImportError:
        return "[Cần cài pdfplumber để đọc PDF]"
    except Exception as e:
        return f"[Lỗi đọc PDF: {e}]"


def process_excel(file_bytes: bytes, file_name: str) -> str:
    """Chuyển Excel/CSV thành text markdown table."""
    try:
        import pandas as pd
        ext = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes), nrows=200)
        else:
            df = pd.read_excel(io.BytesIO(file_bytes), nrows=200)

        # Tóm tắt
        rows, cols = df.shape
        summary = f"File: {file_name} | {rows} dòng × {cols} cột\n"
        summary += f"Cột: {', '.join(str(c) for c in df.columns)}\n\n"
        summary += df.to_markdown(index=False)
        return summary
    except ImportError:
        return "[Cần cài pandas và openpyxl để đọc Excel]"
    except Exception as e:
        return f"[Lỗi đọc Excel: {e}]"


def build_message_with_file(
    text: str,
    file_bytes: bytes,
    file_name: str,
    mime_type: str,
) -> list[dict]:
    """
    Tạo content blocks cho 1 message có kèm file.
    Trả về list[dict] để dùng làm 'content' trong messages API.
    """
    file_type = get_file_type(file_name, mime_type)

    if file_type == "image":
        img_block = process_image(file_bytes, mime_type)
        return [
            img_block,
            {"type": "text", "text": text or "Phân tích hóa đơn/chứng từ trong ảnh này."},
        ]

    if file_type == "pdf":
        extracted = process_pdf(file_bytes)
        combined = f"[NỘI DUNG FILE PDF: {file_name}]\n\n{extracted}\n\n---\n{text or 'Phân tích tài liệu trên.'}"
        return [{"type": "text", "text": combined}]

    if file_type == "excel":
        extracted = process_excel(file_bytes, file_name)
        combined = f"[NỘI DUNG FILE EXCEL: {file_name}]\n\n{extracted}\n\n---\n{text or 'Phân tích dữ liệu trên.'}"
        return [{"type": "text", "text": combined}]

    return [{"type": "text", "text": f"[File {file_name} không hỗ trợ]\n\n{text}"}]
