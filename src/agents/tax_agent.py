"""AI Agent lõi cho INSAKO Tax Agent – tích hợp Claude API."""

import os
import sys

# Đảm bảo UTF-8 trên Linux (Streamlit Cloud)
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from src.utils.helpers import load_all_markdown_from_dir
from src.services.knowledge_service import KnowledgeService


# Cố gắng import anthropic; nếu chưa cài thì dùng fallback nội bộ
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class TaxAgent:
    """Agent tra cứu và kiểm tra nghiệp vụ kế toán – thuế."""

    def __init__(self, config: dict):
        self.config = config
        self.knowledge = KnowledgeService(config)
        self.system_prompt = self.knowledge.get_system_prompt()
        self.kb_content = self.knowledge.get_full_knowledge_base()
        self.history: list[dict] = []

        ai_cfg = config.get("ai", {})
        self.model = ai_cfg.get("model", "claude-sonnet-4-6")
        self.max_tokens = ai_cfg.get("max_tokens", 4096)
        self.api_key = ai_cfg.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))

        self._client = None
        if ANTHROPIC_AVAILABLE and self.api_key and not self.api_key.startswith("YOUR_"):
            self._client = anthropic.Anthropic(api_key=self.api_key)

    def _build_context(self) -> str:
        """Xây dựng context từ knowledge base để đưa vào prompt."""
        return f"""
=== DỮ LIỆU SỔ TAY NỘI BỘ INSAKO ===
{self.kb_content[:6000]}

=== HẾT DỮ LIỆU ===
"""

    def query(self, user_message: str, mode: str = "general") -> str:
        """
        Gửi câu hỏi đến Agent.

        mode: "general" | "check_documents" | "generate_checklist"
        """
        # Thêm prefix hướng dẫn theo mode
        mode_prefix = {
            "general": "",
            "check_documents": (
                "Người dùng muốn KIỂM TRA HỒ SƠ cho nghiệp vụ sau. "
                "Hãy kiểm tra đủ/thiếu chứng từ gì, rủi ro VAT/TNDN/TNCN, "
                "và nên hạch toán ngay hay treo chờ.\n\n"
            ),
            "generate_checklist": (
                "Người dùng muốn TẠO CHECKLIST cho nghiệp vụ sau. "
                "Hãy tạo checklist đầy đủ gồm: hồ sơ cần có, điều kiện VAT, "
                "điều kiện TNDN, hạch toán mẫu, rủi ro thường gặp.\n\n"
            ),
        }

        full_message = mode_prefix.get(mode, "") + user_message

        # Thêm vào lịch sử
        self.history.append({"role": "user", "content": full_message})

        if self._client:
            return self._call_api()
        else:
            return self._local_response(user_message, mode)

    def _call_api(self) -> str:
        """Gọi Claude API qua socket TCP – tránh mọi vấn đề encoding của urllib/httpx."""
        import json as _json
        import socket
        import ssl

        try:
            context = self._build_context()
            system = self.system_prompt + "\n\n" + context

            payload = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": system,
                "messages": self.history,
            }

            # ensure_ascii=True: toàn bộ body là ASCII thuần (Unicode escape \uXXXX)
            # API Claude vẫn decode đúng, response trả về UTF-8 bình thường
            body_str = _json.dumps(payload, ensure_ascii=True)
            body_bytes = body_str.encode("ascii")

            headers = (
                f"POST /v1/messages HTTP/1.1\r\n"
                f"Host: api.anthropic.com\r\n"
                f"x-api-key: {self.api_key}\r\n"
                f"anthropic-version: 2023-06-01\r\n"
                f"content-type: application/json\r\n"
                f"content-length: {len(body_bytes)}\r\n"
                f"connection: close\r\n"
                f"\r\n"
            )

            ctx = ssl.create_default_context()
            with socket.create_connection(("api.anthropic.com", 443), timeout=60) as raw:
                with ctx.wrap_socket(raw, server_hostname="api.anthropic.com") as sock:
                    sock.sendall(headers.encode("ascii") + body_bytes)

                    # Đọc toàn bộ response
                    chunks = []
                    while True:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        chunks.append(chunk)

            raw_response = b"".join(chunks).decode("utf-8", errors="replace")

            # Tách HTTP header và body
            if "\r\n\r\n" in raw_response:
                _, body_part = raw_response.split("\r\n\r\n", 1)
            else:
                body_part = raw_response

            # Xử lý chunked transfer encoding nếu có
            body_part = body_part.strip()
            if "\r\n" in body_part:
                # chunked: bỏ qua chunk-size lines
                lines = body_part.split("\r\n")
                json_lines = [l for l in lines if l and not all(c in "0123456789abcdefABCDEF" for c in l)]
                body_part = "".join(json_lines)

            result = _json.loads(body_part)

            if "error" in result:
                return f"❌ Lỗi API: {result['error'].get('message', str(result['error']))}"

            answer = result["content"][0]["text"]
            self.history.append({"role": "assistant", "content": answer})
            return answer

        except Exception as e:
            return f"❌ Lỗi kết nối API: {type(e).__name__}: {str(e)}"

    def _local_response(self, user_message: str, mode: str) -> str:
        """Phản hồi nội bộ khi không có API key (dựa trên từ khóa + KB)."""
        # Tìm kiếm trong knowledge base
        results = self.knowledge.search_knowledge(user_message)

        response_parts = [
            "💡 [CHẾ ĐỘ CỤC BỘ – Chưa kết nối Claude API]",
            "─" * 50,
        ]

        if mode == "generate_checklist":
            # Tìm checklist phù hợp
            checklist = self._find_relevant_checklist(user_message)
            if checklist:
                response_parts.append(checklist)
            else:
                response_parts.append(self._generate_basic_checklist(user_message))
        elif mode == "check_documents":
            response_parts.append(self._check_documents_local(user_message, results))
        else:
            response_parts.append(self._general_answer_local(user_message, results))

        response_parts.append("\n" + "─" * 50)
        response_parts.append(
            "⚠️ Để có câu trả lời chính xác hơn, hãy thêm ANTHROPIC_API_KEY vào config.json\n"
            "⚠️ Cần đối chiếu với quy định pháp luật hiện hành và tư vấn chuyên gia trước khi áp dụng."
        )

        answer = "\n".join(response_parts)
        self.history.append({"role": "assistant", "content": answer})
        return answer

    @staticmethod
    def _normalize(text: str) -> str:
        import unicodedata
        nfkd = unicodedata.normalize("NFKD", text.lower())
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def _find_relevant_checklist(self, query: str) -> str:
        """Tìm checklist phù hợp với câu hỏi."""
        keywords_map = {
            "luong": "luong_kpi", "kpi": "luong_kpi", "thuong": "luong_kpi",
            "mua hang": "chi_phi_mua_hang", "vat tu": "chi_phi_mua_hang", "hoa don": "chi_phi_mua_hang",
            "tam ung": "tam_ung_hoan_ung", "hoan ung": "tam_ung_hoan_ung", "cong tac phi": "tam_ung_hoan_ung",
        }
        query_lower = self._normalize(query)
        for kw, checklist_name in keywords_map.items():
            if kw in query_lower:
                return self.knowledge.get_checklist_by_name(checklist_name)
        return ""

    def _generate_basic_checklist(self, query: str) -> str:
        """Tạo checklist cơ bản dựa trên mẫu template."""
        return f"""
📋 CHECKLIST CƠ BẢN CHO: {query.upper()}
{'═' * 50}

📄 HỒ SƠ CẦN CÓ:
  ☐ [BẮT BUỘC] Hóa đơn GTGT hợp lệ
  ☐ [BẮT BUỘC] Chứng từ thanh toán (CK nếu > 20 triệu)
  ☐ [BẮT BUỘC] Hợp đồng/Đặt hàng (nếu > 20 triệu)
  ☐ [NÊN CÓ]   Biên bản nghiệm thu / Giao nhận
  ☐ [NÊN CÓ]   Phê duyệt nội bộ

✅ ĐIỀU KIỆN KHẤU TRỪ VAT:
  ☐ Hóa đơn VAT hợp lệ?
  ☐ Thanh toán chuyển khoản (nếu > 20tr)?
  ☐ Dùng cho hoạt động chịu thuế?

✅ ĐIỀU KIỆN CHI PHÍ TNDN:
  ☐ Thực tế phát sinh, gắn SXKD?
  ☐ Có đủ chứng từ hợp lệ?

⚠️  RỦI RO CẦN LƯU Ý:
  🟡 Kiểm tra ngưỡng thanh toán tiền mặt (> 20 triệu)
  🟡 Kiểm tra tính hợp lệ của hóa đơn
  🟡 Đảm bảo ghi nhận đúng kỳ

💡 Để có checklist chi tiết hơn cho nghiệp vụ cụ thể,
   vui lòng kết nối Claude API trong config.json
"""

    def _check_documents_local(self, query: str, kb_results: list) -> str:
        """Kiểm tra hồ sơ cơ bản dựa trên KB."""
        base_check = f"""
📋 KIỂM TRA HỒ SƠ: {query}
{'═' * 50}

🔍 DỰA TRÊN KNOWLEDGE BASE NỘI BỘ:
"""
        if kb_results:
            base_check += "\nTìm thấy thông tin liên quan:\n"
            for r in kb_results[:2]:
                base_check += f"\n📄 [{r['file']}]:\n{r['excerpt'][:300]}...\n"
        else:
            base_check += "\nKhông tìm thấy thông tin cụ thể trong KB.\n"

        base_check += """
☑️  KIỂM TRA CHUNG:
  ☐ Có hóa đơn GTGT hợp lệ không?
  ☐ Hình thức thanh toán có đúng quy định không? (> 20tr → CK)
  ☐ Hồ sơ có gắn với nghiệp vụ thực tế không?
  ☐ Đã có phê duyệt nội bộ theo phân quyền chưa?
"""
        return base_check

    def _general_answer_local(self, query: str, kb_results: list) -> str:
        """Trả lời chung dựa trên KB."""
        if not kb_results:
            return (
                f"Không tìm thấy thông tin cụ thể về '{query}' trong Knowledge Base nội bộ.\n"
                "Vui lòng kết nối Claude API để nhận câu trả lời chi tiết hơn."
            )

        answer = f"📚 Thông tin tìm thấy trong KB về: '{query}'\n\n"
        for i, r in enumerate(kb_results[:3], 1):
            answer += f"[{i}] 📄 {r['file']}:\n{r['excerpt'][:400]}\n\n"
        return answer

    def clear_history(self) -> None:
        """Xóa lịch sử hội thoại."""
        self.history = []
