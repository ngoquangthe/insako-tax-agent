"""Công cụ xuất báo cáo rủi ro."""

from datetime import datetime
from pathlib import Path
from src.utils.helpers import format_currency, risk_emoji, today_str


class ReportTool:
    """Tạo báo cáo rủi ro từ danh sách cases."""

    def __init__(self, config: dict):
        self.config = config
        self.output_dir = Path(config.get("paths", {}).get("outputs", "outputs"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_risk_report(self, cases: list[dict], summary: dict) -> str:
        """Tạo báo cáo rủi ro dạng Markdown."""
        today = today_str()
        report_lines = [
            "# BÁO CÁO RỦI RO THUẾ – INSAKO",
            f"\n> Xuất ngày: {today} | Tổng số case: {summary.get('total_cases', 0)}",
            "\n---\n",
            "## 1. TỔNG QUAN",
            "",
            f"- **Tổng số lỗi ghi nhận:** {summary.get('total_cases', 0)}",
            f"- **Tổng thiệt hại ước tính:** {format_currency(summary.get('total_loss_estimated', 0))}",
            "",
            "### Phân loại theo trạng thái",
            "",
        ]

        for status, count in summary.get("by_status", {}).items():
            report_lines.append(f"- {status}: **{count}** case")

        report_lines += [
            "",
            "### Phân loại theo loại thuế",
            "",
        ]
        for tax_type, count in summary.get("by_tax_type", {}).items():
            report_lines.append(f"- Rủi ro {tax_type}: **{count}** case")

        report_lines += [
            "\n---\n",
            "## 2. CHI TIẾT TỪNG CASE",
            "",
        ]

        for case in cases:
            risks = case.get("tax_risks", {})
            risk_display = ", ".join(
                f"{k.upper()}: {risk_emoji(v)} {v}"
                for k, v in risks.items()
                if v and v.lower() not in ("không", "none", "")
            )

            prevention = case.get("prevention", [])
            prev_text = "\n  - ".join(prevention) if prevention else "Chưa có"

            report_lines += [
                f"### {case.get('id', '')} – {case.get('business_type', '')}",
                "",
                f"| Trường | Nội dung |",
                f"|--------|----------|",
                f"| Ngày phát hiện | {case.get('date_found', '')} |",
                f"| Kỳ phát sinh | {case.get('period', '')} |",
                f"| Phòng ban | {', '.join(case.get('department', []))} |",
                f"| Rủi ro thuế | {risk_display} |",
                f"| Thiệt hại | {format_currency(case.get('total_loss', 0))} |",
                f"| Trạng thái | {case.get('status', '')} |",
                "",
                f"**Mô tả:** {case.get('description', '')}",
                "",
                f"**Nguyên nhân:** {case.get('root_cause', '')}",
                "",
                f"**Phòng ngừa:**\n  - {prev_text}",
                "",
                "---",
                "",
            ]

        report_lines += [
            "## 3. KHUYẾN NGHỊ ƯU TIÊN",
            "",
            "1. Rà soát và cập nhật Quy chế lương thưởng KPI trước mỗi năm tài chính",
            "2. Kiểm tra 100% hóa đơn > 20 triệu có chứng từ chuyển khoản kèm theo",
            "3. Ban hành mẫu Biên bản tiếp khách bắt buộc cho mọi chi phí > 2 triệu",
            "4. Thực hiện soát xét hồ sơ kế toán định kỳ hàng quý",
            "",
            "---",
            "",
            "> ⚠️ *Báo cáo này chỉ mang tính nội bộ. Mọi quyết định thuế cần được xác nhận",
            "> bởi chuyên gia thuế có chứng chỉ hành nghề.*",
        ]

        return "\n".join(report_lines)

    def save_report(self, content: str, filename: str = "") -> str:
        """Lưu báo cáo ra file và trả về đường dẫn."""
        if not filename:
            filename = f"risk_report_{today_str()}.md"
        output_path = self.output_dir / filename
        output_path.write_text(content, encoding="utf-8")
        return str(output_path)
