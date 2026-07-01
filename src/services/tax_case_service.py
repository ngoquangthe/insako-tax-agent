"""Dịch vụ quản lý nhật ký lỗi quyết toán thuế."""

from datetime import datetime
from src.utils.helpers import load_json, save_json, next_case_id, format_currency, format_date


class TaxCaseService:
    """Quản lý CRUD cho nhật ký lỗi quyết toán thuế."""

    def __init__(self, config: dict):
        db_path = config.get("database", {}).get("tax_cases_file", "data/tax_cases/cases_db.json")
        self.db_path = db_path
        self._db = None

    def _load(self) -> dict:
        if self._db is None:
            self._db = load_json(self.db_path)
            if not self._db:
                self._db = {
                    "version": "1.0",
                    "company": "INSAKO",
                    "last_updated": datetime.now().strftime("%Y-%m-%d"),
                    "cases": [],
                    "summary": {"total_cases": 0, "total_loss_estimated": 0,
                                "by_status": {}, "by_tax_type": {}}
                }
        return self._db

    def _save(self) -> None:
        db = self._load()
        db["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        self._update_summary(db)
        save_json(db, self.db_path)

    def _update_summary(self, db: dict) -> None:
        cases = db.get("cases", [])
        total_loss = sum(c.get("total_loss", 0) for c in cases)
        by_status: dict = {}
        by_tax: dict = {}

        for c in cases:
            st = c.get("status", "Không rõ")
            by_status[st] = by_status.get(st, 0) + 1
            for tax_type, risk in c.get("tax_risks", {}).items():
                if risk and risk.lower() not in ("không", "none", ""):
                    tax_key = tax_type.upper()
                    by_tax[tax_key] = by_tax.get(tax_key, 0) + 1

        db["summary"] = {
            "total_cases": len(cases),
            "total_loss_estimated": total_loss,
            "by_status": by_status,
            "by_tax_type": by_tax,
        }

    def add_case(self, case_data: dict) -> str:
        """Thêm case lỗi mới. Trả về ID của case."""
        db = self._load()
        cases = db.setdefault("cases", [])

        case_id = next_case_id(cases)
        new_case = {
            "id": case_id,
            "stt": len(cases) + 1,
            "date_found": case_data.get("date_found", datetime.now().strftime("%Y-%m-%d")),
            "found_by": case_data.get("found_by", ""),
            "source": case_data.get("source", "Tự kiểm tra"),
            "business_type": case_data.get("business_type", ""),
            "period": case_data.get("period", ""),
            "description": case_data.get("description", ""),
            "department": case_data.get("department", []),
            "root_cause": case_data.get("root_cause", ""),
            "tax_risks": case_data.get("tax_risks", {"vat": "", "tndn": "", "tncn": "", "bhxh": ""}),
            "amount_affected": case_data.get("amount_affected", 0),
            "tax_amount": case_data.get("tax_amount", 0),
            "penalty": case_data.get("penalty", 0),
            "late_payment": case_data.get("late_payment", 0),
            "total_loss": case_data.get("total_loss", 0),
            "current_handling": case_data.get("current_handling", ""),
            "prevention": case_data.get("prevention", []),
            "process_to_fix": case_data.get("process_to_fix", ""),
            "responsible": case_data.get("responsible", ""),
            "status": case_data.get("status", "Mới phát hiện"),
            "notes": case_data.get("notes", ""),
        }
        cases.append(new_case)
        self._save()
        return case_id

    def list_cases(self, status_filter: str = "") -> list[dict]:
        """Liệt kê tất cả cases, có thể lọc theo trạng thái."""
        db = self._load()
        cases = db.get("cases", [])
        if status_filter:
            cases = [c for c in cases if status_filter.lower() in c.get("status", "").lower()]
        return cases

    def get_case(self, case_id: str) -> dict | None:
        """Lấy thông tin chi tiết một case."""
        db = self._load()
        for case in db.get("cases", []):
            if case.get("id") == case_id:
                return case
        return None

    def update_case_status(self, case_id: str, new_status: str) -> bool:
        """Cập nhật trạng thái xử lý của case."""
        db = self._load()
        for case in db.get("cases", []):
            if case.get("id") == case_id:
                case["status"] = new_status
                self._save()
                return True
        return False

    def get_summary(self) -> dict:
        """Lấy thống kê tổng hợp."""
        db = self._load()
        return db.get("summary", {})

    def format_case_display(self, case: dict) -> str:
        """Định dạng case để hiển thị."""
        risks = case.get("tax_risks", {})
        risk_str = " | ".join(
            f"{k.upper()}: {v}" for k, v in risks.items() if v and v.lower() not in ("không", "")
        )

        prevention = case.get("prevention", [])
        prev_str = "\n  ".join(f"• {p}" for p in prevention) if prevention else "Chưa có"

        return f"""
{'═' * 60}
📋 {case.get('id', '')} – {case.get('business_type', '')}
{'═' * 60}
📅 Ngày phát hiện : {format_date(case.get('date_found', ''))}
🏢 Phòng ban      : {', '.join(case.get('department', []))}
📌 Kỳ phát sinh   : {case.get('period', '')}

📝 Mô tả sai sót:
  {case.get('description', '')}

🔍 Nguyên nhân gốc rễ:
  {case.get('root_cause', '')}

⚠️  Rủi ro thuế: {risk_str}

💰 Thiệt hại ước tính:
  • Thuế truy thu : {format_currency(case.get('tax_amount', 0))}
  • Tiền phạt     : {format_currency(case.get('penalty', 0))}
  • Chậm nộp      : {format_currency(case.get('late_payment', 0))}
  • Tổng thiệt hại: {format_currency(case.get('total_loss', 0))}

🛠️  Cách xử lý hiện tại:
  {case.get('current_handling', '')}

🛡️  Cách phòng ngừa:
  {prev_str}

👤 Người chịu TN  : {case.get('responsible', '')}
🔖 Trạng thái     : {case.get('status', '')}
"""

    def format_list_display(self, cases: list[dict]) -> str:
        """Định dạng danh sách cases ngắn gọn."""
        if not cases:
            return "  Chưa có case nào được ghi nhận."

        lines = [f"\n{'Mã Case':<18} {'Nghiệp vụ':<30} {'Thiệt hại':>15} {'Trạng thái'}", "─" * 80]
        for c in cases:
            lines.append(
                f"  {c.get('id', ''):<16} {c.get('business_type', '')[:28]:<30} "
                f"{format_currency(c.get('total_loss', 0)):>15} {c.get('status', '')}"
            )
        return "\n".join(lines)
