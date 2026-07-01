#!/usr/bin/env python3
"""
AI AGENT SỔ TAY KẾ TOÁN – THUẾ – TÀI CHÍNH INSAKO
Điểm khởi chạy chính (CLI)
"""

import json
import os
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from src.agents.tax_agent import TaxAgent
from src.services.tax_case_service import TaxCaseService
from src.tools.report_tool import ReportTool
from src.utils.helpers import print_header, print_separator, today_str


# ── Màu sắc terminal (nếu hỗ trợ) ──────────────────────────────────────────
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def load_config() -> dict:
    """Đọc config.json, fallback về config.example.json."""
    for cfg_file in ["config.json", "config.example.json"]:
        cfg_path = ROOT / cfg_file
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
    return {}


def print_welcome() -> None:
    """Hiển thị màn hình chào."""
    print()
    print(f"{CYAN}{'╔' + '═' * 58 + '╗'}{RESET}")
    print(f"{CYAN}║{BOLD}   🏭 AI AGENT SỔ TAY KẾ TOÁN – THUẾ – INSAKO          {RESET}{CYAN}║{RESET}")
    print(f"{CYAN}║   Phiên bản 1.0 | Công ty CP ĐT&TM Thế Nam            ║{RESET}")
    print(f"{CYAN}{'╚' + '═' * 58 + '╝'}{RESET}")
    print()
    print(f"  📅 Ngày: {today_str()}")
    print(f"  📌 Lưu ý: Mọi câu trả lời chỉ mang tính tham khảo.")
    print(f"  📌 Cần xác nhận của Kế toán trưởng / Chuyên gia thuế.")
    print()


def print_main_menu() -> None:
    """Hiển thị menu chính."""
    print(f"\n{BOLD}═══ MENU CHÍNH ═══{RESET}")
    print("  1. 🔍 Tra cứu nghiệp vụ kế toán – thuế")
    print("  2. ✅ Kiểm tra hồ sơ khoản chi")
    print("  3. 📋 Tạo checklist nghiệp vụ")
    print("  4. ➕ Ghi nhận lỗi quyết toán thuế")
    print("  5. 📜 Xem danh sách lỗi đã ghi nhận")
    print("  6. 📊 Xuất báo cáo rủi ro")
    print("  7. 🔄 Xóa lịch sử hội thoại")
    print("  0. 🚪 Thoát")
    print()


def get_input(prompt: str) -> str:
    """Lấy input từ người dùng, xử lý Ctrl+C."""
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n[Ctrl+C] Quay về menu chính...")
        return ""


def menu_query_business(agent: TaxAgent) -> None:
    """Menu 1: Tra cứu nghiệp vụ."""
    print_header("🔍 TRA CỨU NGHIỆP VỤ KẾ TOÁN – THUẾ")
    print("  Nhập câu hỏi về nghiệp vụ. Gõ 'back' để quay lại.\n")
    print("  Ví dụ:")
    print("  • Chi phí thuê vận chuyển hạt bi thép từ cảng về kho")
    print("  • Chi phí tiếp khách ký hợp đồng bán máy phun bi")
    print("  • Lương KPI cho nhân viên kinh doanh tháng 6")
    print("  • Nhập khẩu máy phun bi từ Trung Quốc\n")

    while True:
        user_input = get_input(f"\n{GREEN}Câu hỏi của bạn:{RESET} ")
        if not user_input or user_input.lower() in ("back", "b", "0"):
            break

        print(f"\n{YELLOW}⏳ Đang xử lý...{RESET}\n")
        response = agent.query(user_input, mode="general")
        print(response)
        print(f"\n{CYAN}─── Hết câu trả lời ───{RESET}")


def menu_check_documents(agent: TaxAgent) -> None:
    """Menu 2: Kiểm tra hồ sơ."""
    print_header("✅ KIỂM TRA HỒ SƠ KHOẢN CHI")
    print("  Mô tả khoản chi hoặc nghiệp vụ cần kiểm tra hồ sơ.\n")
    print("  Ví dụ:")
    print("  • Chi phí sửa chữa máy phun bi tại xưởng khách hàng 50 triệu")
    print("  • Mua 10 tấn hạt bi thép, thanh toán tiền mặt 45 triệu")
    print("  • Thuê nhân công lắp đặt máy phun bi, cá nhân, không HĐLĐ\n")

    while True:
        user_input = get_input(f"\n{GREEN}Mô tả nghiệp vụ cần kiểm tra:{RESET} ")
        if not user_input or user_input.lower() in ("back", "b", "0"):
            break

        print(f"\n{YELLOW}⏳ Đang kiểm tra...{RESET}\n")
        response = agent.query(user_input, mode="check_documents")
        print(response)


def menu_generate_checklist(agent: TaxAgent) -> None:
    """Menu 3: Tạo checklist."""
    print_header("📋 TẠO CHECKLIST NGHIỆP VỤ")
    print("  Chọn nghiệp vụ hoặc nhập tên nghiệp vụ cần tạo checklist:\n")
    print("  Danh sách nhanh:")
    print("   [1]  Lương & KPI                [2]  Mua vật tư, hàng hóa")
    print("   [3]  Tạm ứng & Hoàn ứng         [4]  Nhập khẩu")
    print("   [5]  Tiếp khách                 [6]  Công tác phí")
    print("   [7]  Thuê ngoài (gia công, lắp) [8]  Tài sản cố định")
    print("   [9]  Doanh thu / Xuất hóa đơn   [10] Chi phí không có hóa đơn")
    print("   Hoặc nhập tên nghiệp vụ bất kỳ\n")

    quick_map = {
        "1": "Lương và KPI nhân viên",
        "2": "Mua vật tư hàng hóa",
        "3": "Tạm ứng và hoàn ứng công tác phí",
        "4": "Nhập khẩu máy móc hàng hóa",
        "5": "Chi phí tiếp khách",
        "6": "Chi phí công tác phí",
        "7": "Thuê ngoài gia công lắp đặt",
        "8": "Tài sản cố định mua mới",
        "9": "Ghi nhận doanh thu xuất hóa đơn",
        "10": "Chi phí không có hóa đơn",
    }

    while True:
        user_input = get_input(f"\n{GREEN}Chọn số hoặc nhập tên nghiệp vụ:{RESET} ")
        if not user_input or user_input.lower() in ("back", "b", "0"):
            break

        query = quick_map.get(user_input, user_input)
        print(f"\n{YELLOW}⏳ Đang tạo checklist cho: {query}...{RESET}\n")
        response = agent.query(f"Tạo checklist đầy đủ cho: {query}", mode="generate_checklist")
        print(response)

        save = get_input("\nLưu checklist này ra file? (y/n): ")
        if save.lower() == "y":
            filename = f"outputs/checklist_{query[:20].replace(' ', '_')}_{today_str()}.md"
            Path("outputs").mkdir(exist_ok=True)
            Path(filename).write_text(response, encoding="utf-8")
            print(f"{GREEN}✅ Đã lưu: {filename}{RESET}")


def menu_add_tax_case(case_service: TaxCaseService) -> None:
    """Menu 4: Ghi nhận lỗi quyết toán thuế."""
    print_header("➕ GHI NHẬN LỖI QUYẾT TOÁN THUẾ")
    print("  Nhập thông tin lỗi theo từng bước. Nhấn Enter để bỏ qua (optional).\n")

    print(f"{YELLOW}Bước 1/5 – Thông tin cơ bản{RESET}")
    business_type = get_input("  Nghiệp vụ bị lỗi: ")
    if not business_type:
        print("Hủy bỏ.")
        return

    period = get_input("  Kỳ phát sinh (VD: 2025, Q1/2025): ")
    description = get_input("  Mô tả sai sót (ngắn gọn): ")
    department = get_input("  Phòng ban liên quan (VD: Kế toán, Kinh doanh): ")
    departments = [d.strip() for d in department.split(",") if d.strip()]

    print(f"\n{YELLOW}Bước 2/5 – Nguyên nhân{RESET}")
    root_cause = get_input("  Nguyên nhân gốc rễ: ")

    print(f"\n{YELLOW}Bước 3/5 – Rủi ro thuế{RESET}")
    vat_risk = get_input("  Rủi ro VAT (Thấp/Trung bình/Cao/Không): ") or "Không"
    tndn_risk = get_input("  Rủi ro TNDN (Thấp/Trung bình/Cao/Không): ") or "Không"
    tncn_risk = get_input("  Rủi ro TNCN (Thấp/Trung bình/Cao/Không): ") or "Không"
    bhxh_risk = get_input("  Rủi ro BHXH (Thấp/Trung bình/Cao/Không): ") or "Không"

    print(f"\n{YELLOW}Bước 4/5 – Tài chính{RESET}")
    try:
        tax_amount = int(get_input("  Thuế truy thu (VNĐ, Enter nếu chưa biết): ") or "0")
        penalty = int(get_input("  Tiền phạt (VNĐ): ") or "0")
        late_payment = int(get_input("  Tiền chậm nộp (VNĐ): ") or "0")
    except ValueError:
        tax_amount = penalty = late_payment = 0

    print(f"\n{YELLOW}Bước 5/5 – Xử lý & Phòng ngừa{RESET}")
    current_handling = get_input("  Cách xử lý hiện tại: ")
    prevention_raw = get_input("  Biện pháp phòng ngừa (phân cách bằng |): ")
    prevention = [p.strip() for p in prevention_raw.split("|") if p.strip()]
    process_to_fix = get_input("  Quy trình cần sửa: ")
    responsible = get_input("  Người chịu trách nhiệm: ")

    case_data = {
        "business_type": business_type,
        "period": period,
        "description": description,
        "department": departments,
        "root_cause": root_cause,
        "tax_risks": {"vat": vat_risk, "tndn": tndn_risk, "tncn": tncn_risk, "bhxh": bhxh_risk},
        "tax_amount": tax_amount,
        "penalty": penalty,
        "late_payment": late_payment,
        "total_loss": tax_amount + penalty + late_payment,
        "current_handling": current_handling,
        "prevention": prevention,
        "process_to_fix": process_to_fix,
        "responsible": responsible,
        "status": "Mới phát hiện",
        "found_by": "Kế toán nội bộ",
        "source": "Tự kiểm tra",
    }

    confirm = get_input(f"\n{YELLOW}Xác nhận lưu case này? (y/n):{RESET} ")
    if confirm.lower() == "y":
        case_id = case_service.add_case(case_data)
        print(f"\n{GREEN}✅ Đã lưu case: {case_id}{RESET}")
    else:
        print("Đã hủy.")


def menu_view_cases(case_service: TaxCaseService) -> None:
    """Menu 5: Xem danh sách lỗi."""
    print_header("📜 DANH SÁCH LỖI QUYẾT TOÁN THUẾ")

    print("  Lọc theo trạng thái:")
    print("  [Enter] Tất cả  |  [1] Mới phát hiện  |  [2] Đang xử lý")
    print("  [3] Đã xử lý    |  [4] Đang theo dõi  |  [id] Xem chi tiết\n")

    filter_map = {"1": "Mới phát hiện", "2": "Đang xử lý", "3": "Đã xử lý", "4": "Đang theo dõi"}
    choice = get_input("Chọn: ")
    status_filter = filter_map.get(choice, "")

    cases = case_service.list_cases(status_filter)
    summary = case_service.get_summary()

    print(f"\n📊 Tổng cộng: {summary.get('total_cases', 0)} case | "
          f"Tổng thiệt hại: {summary.get('total_loss_estimated', 0):,.0f} đ\n")
    print(case_service.format_list_display(cases))

    while True:
        case_id = get_input("\nNhập mã case để xem chi tiết (Enter để quay lại): ")
        if not case_id:
            break
        case = case_service.get_case(case_id.upper())
        if case:
            print(case_service.format_case_display(case))
            update = get_input("Cập nhật trạng thái? (y/n): ")
            if update.lower() == "y":
                print("  [1] Mới phát hiện  [2] Đang xử lý  [3] Đã xử lý  [4] Đang theo dõi")
                status_choice = get_input("Chọn: ")
                new_status = filter_map.get(status_choice)
                if new_status:
                    case_service.update_case_status(case_id.upper(), new_status)
                    print(f"{GREEN}✅ Đã cập nhật trạng thái: {new_status}{RESET}")
        else:
            print(f"{RED}Không tìm thấy case: {case_id}{RESET}")


def menu_export_report(case_service: TaxCaseService, report_tool: ReportTool) -> None:
    """Menu 6: Xuất báo cáo rủi ro."""
    print_header("📊 XUẤT BÁO CÁO RỦI RO")

    cases = case_service.list_cases()
    summary = case_service.get_summary()

    if not cases:
        print("  Chưa có case nào để xuất báo cáo.")
        return

    print(f"  Sẽ xuất báo cáo gồm {len(cases)} case...\n")
    confirm = get_input("Xác nhận xuất báo cáo? (y/n): ")
    if confirm.lower() != "y":
        return

    content = report_tool.generate_risk_report(cases, summary)
    file_path = report_tool.save_report(content)
    print(f"\n{GREEN}✅ Đã xuất báo cáo: {file_path}{RESET}")
    print("\n📋 Xem trước (20 dòng đầu):")
    print_separator("─")
    lines = content.split("\n")[:20]
    print("\n".join(lines))
    print("...")


def main() -> None:
    """Hàm chính – vòng lặp CLI."""
    config = load_config()

    if not config:
        print(f"{RED}❌ Không tìm thấy config.json. Hãy tạo từ config.example.json{RESET}")
        sys.exit(1)

    # Khởi tạo services
    agent = TaxAgent(config)
    case_service = TaxCaseService(config)
    report_tool = ReportTool(config)

    # Kiểm tra trạng thái AI
    ai_status = f"{GREEN}✅ Claude API{RESET}" if agent._client else f"{YELLOW}⚠️  Chế độ cục bộ (KB-only){RESET}"

    print_welcome()
    print(f"  Trạng thái AI: {ai_status}")

    while True:
        print_main_menu()
        choice = get_input(f"{BOLD}Chọn chức năng (0-7):{RESET} ")

        if choice == "1":
            menu_query_business(agent)
        elif choice == "2":
            menu_check_documents(agent)
        elif choice == "3":
            menu_generate_checklist(agent)
        elif choice == "4":
            menu_add_tax_case(case_service)
        elif choice == "5":
            menu_view_cases(case_service)
        elif choice == "6":
            menu_export_report(case_service, report_tool)
        elif choice == "7":
            agent.clear_history()
            print(f"{GREEN}✅ Đã xóa lịch sử hội thoại.{RESET}")
        elif choice == "0":
            print("\n👋 Tạm biệt! Chúc kế toán INSAKO làm việc hiệu quả.\n")
            sys.exit(0)
        else:
            print(f"{RED}Lựa chọn không hợp lệ. Vui lòng chọn 0-7.{RESET}")


if __name__ == "__main__":
    main()
