"""Dịch vụ quản lý Knowledge Base cho INSAKO Tax Agent."""

from pathlib import Path
from src.utils.helpers import load_markdown, load_all_markdown_from_dir


class KnowledgeService:
    """Tải và tìm kiếm trong Knowledge Base."""

    def __init__(self, config: dict):
        self.config = config
        self.paths = config.get("paths", {})
        self._cache: dict[str, str] = {}

    def get_system_prompt(self) -> str:
        """Đọc system prompt từ file."""
        prompt_file = self.config.get("ai", {}).get("system_prompt_file", "")
        return load_markdown(prompt_file)

    def get_full_knowledge_base(self) -> str:
        """Lấy toàn bộ knowledge base (tất cả file .md)."""
        if "full_kb" in self._cache:
            return self._cache["full_kb"]

        parts = []
        for key in ["knowledge_base", "checklists", "accounting_rules", "legal_references"]:
            dir_path = self.paths.get(key, "")
            if dir_path:
                content = load_all_markdown_from_dir(dir_path)
                if content:
                    parts.append(content)

        result = "\n\n".join(parts)
        self._cache["full_kb"] = result
        return result

    def get_checklist_content(self) -> str:
        """Lấy tất cả checklist."""
        dir_path = self.paths.get("checklists", "")
        return load_all_markdown_from_dir(dir_path)

    @staticmethod
    def _normalize(text: str) -> str:
        """Chuyển về chữ thường, bỏ dấu cơ bản để tìm kiếm mềm hơn."""
        import unicodedata
        nfkd = unicodedata.normalize("NFKD", text.lower())
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def search_knowledge(self, query: str) -> list[dict]:
        """Tìm kiếm từ khóa trong knowledge base (tìm kiếm đơn giản)."""
        results = []
        query_lower = query.lower()
        query_norm = self._normalize(query)

        for key in ["knowledge_base", "checklists", "accounting_rules"]:
            dir_path = Path(self.paths.get(key, ""))
            if not dir_path.exists():
                continue

            for md_file in dir_path.glob("*.md"):
                content = md_file.read_text(encoding="utf-8")
                content_norm = self._normalize(content)
                if query_lower in content.lower() or query_norm in content_norm:
                    # Trích đoạn liên quan
                    lines = content.split("\n")
                    relevant_lines = []
                    for i, line in enumerate(lines):
                        if query_lower in line.lower() or query_norm in self._normalize(line):
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            relevant_lines.extend(lines[start:end])

                    results.append({
                        "file": md_file.name,
                        "category": key,
                        "excerpt": "\n".join(relevant_lines[:20]),
                    })

        return results

    def list_available_checklists(self) -> list[str]:
        """Liệt kê tên các checklist có sẵn."""
        dir_path = Path(self.paths.get("checklists", ""))
        if not dir_path.exists():
            return []
        return [f.stem for f in dir_path.glob("*.md")]

    def get_checklist_by_name(self, name: str) -> str:
        """Lấy nội dung checklist theo tên."""
        dir_path = Path(self.paths.get("checklists", ""))
        for f in dir_path.glob("*.md"):
            if name.lower() in f.stem.lower():
                return f.read_text(encoding="utf-8")
        return ""
