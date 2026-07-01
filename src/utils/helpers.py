"""Tiện ích chung cho INSAKO Tax Agent."""

import json
import os
from datetime import datetime
from pathlib import Path


def load_json(file_path: str) -> dict:
    """Đọc file JSON, trả về dict rỗng nếu không tồn tại."""
    path = Path(file_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, file_path: str) -> None:
    """Ghi dữ liệu ra file JSON."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_markdown(file_path: str) -> str:
    """Đọc nội dung file Markdown."""
    path = Path(file_path)
    if not path.exists():
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_all_markdown_from_dir(directory: str) -> str:
    """Đọc và nối tất cả file .md trong thư mục."""
    path = Path(directory)
    if not path.exists():
        return ""
    content = []
    for md_file in sorted(path.glob("*.md")):
        content.append(f"\n\n--- {md_file.name} ---\n")
        content.append(md_file.read_text(encoding="utf-8"))
    return "".join(content)


def format_currency(amount: int | float) -> str:
    """Định dạng số tiền VNĐ."""
    return f"{amount:,.0f} đ"


def format_date(date_str: str) -> str:
    """Chuyển YYYY-MM-DD sang DD/MM/YYYY."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_str


def today_str() -> str:
    """Trả về ngày hôm nay dạng YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def next_case_id(cases: list) -> str:
    """Tạo mã case tiếp theo theo định dạng CASE-YYYY-NNN."""
    year = datetime.now().year
    existing = [c.get("id", "") for c in cases]
    year_cases = [c for c in existing if f"CASE-{year}-" in c]
    if not year_cases:
        return f"CASE-{year}-001"
    nums = [int(c.split("-")[-1]) for c in year_cases]
    return f"CASE-{year}-{max(nums) + 1:03d}"


def risk_emoji(level: str) -> str:
    """Chuyển mức rủi ro sang emoji màu."""
    mapping = {
        "thấp": "🟢", "low": "🟢",
        "trung bình": "🟡", "medium": "🟡",
        "cao": "🔴", "high": "🔴",
        "không": "⚪", "none": "⚪",
    }
    return mapping.get(level.lower(), "⚫")


def print_separator(char: str = "═", width: int = 60) -> None:
    """In dòng phân cách."""
    print(char * width)


def print_header(title: str) -> None:
    """In tiêu đề có viền."""
    print()
    print_separator()
    print(f"  {title}")
    print_separator()
