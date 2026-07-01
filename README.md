# AI AGENT SỔ TAY KẾ TOÁN – THUẾ – TÀI CHÍNH INSAKO

> Phiên bản: 1.0.0 | Cập nhật: 2026-07-01
> Công ty: INSAKO (Công ty CP Đầu tư và Thương mại Thế Nam)

---

## Giới thiệu

**INSAKO Tax Agent** là hệ thống AI hỗ trợ kế toán nội bộ, giúp:

- Tra cứu nghiệp vụ kế toán – thuế theo đúng quy định pháp luật VN
- Kiểm tra hồ sơ chứng từ trước khi hạch toán
- Tạo checklist tự động cho từng nhóm nghiệp vụ
- Ghi nhận và phòng ngừa lỗi quyết toán thuế
- Đánh giá rủi ro thuế GTGT, TNDN, TNCN, BHXH

**Lĩnh vực áp dụng:** Máy phun bi, phun cát, phụ tùng, hạt bi thép, dịch vụ bảo trì công nghiệp.

---

## Cấu trúc dự án

```
insako-tax-agent/
├── data/
│   ├── knowledge_base/     # Quy định, nghiệp vụ, căn cứ pháp lý
│   ├── checklists/         # Checklist từng nhóm nghiệp vụ
│   ├── templates/          # Biểu mẫu chứng từ nội bộ
│   ├── tax_cases/          # Nhật ký lỗi quyết toán thuế
│   ├── accounting_rules/   # Quy tắc hạch toán nội bộ
│   └── legal_references/   # Văn bản pháp luật tham chiếu
├── src/
│   ├── agents/             # Logic AI Agent
│   ├── tools/              # Công cụ tra cứu, kiểm tra
│   ├── prompts/            # Prompt hệ thống
│   ├── services/           # Dịch vụ xử lý dữ liệu
│   └── utils/              # Tiện ích chung
├── docs/
│   ├── manual/             # Hướng dẫn sử dụng
│   ├── processes/          # Quy trình nội bộ
│   └── forms/              # Biểu mẫu
├── outputs/                # Kết quả xuất ra (checklist, báo cáo)
├── main.py                 # Điểm khởi chạy CLI
├── config.example.json     # Cấu hình mẫu
└── requirements.txt        # Thư viện Python
```

---

## Cài đặt

### Yêu cầu
- Python 3.9+
- pip

### Các bước

```bash
# 1. Clone hoặc copy dự án
cd insako-tax-agent

# 2. Tạo môi trường ảo
python -m venv venv

# Windows
venv\Scripts\activate

# 3. Cài thư viện
pip install -r requirements.txt

# 4. Tạo file cấu hình
copy config.example.json config.json
# Chỉnh sửa config.json với API key của bạn

# 5. Chạy chương trình
python main.py
```

---

## Hướng dẫn sử dụng nhanh

### Chạy CLI

```bash
python main.py
```

Chọn menu:
```
1. Tra cứu nghiệp vụ
2. Kiểm tra hồ sơ khoản chi
3. Tạo checklist nghiệp vụ
4. Ghi nhận lỗi quyết toán thuế
5. Xem danh sách lỗi sai
6. Xuất báo cáo rủi ro
7. Thoát
```

### Ví dụ câu hỏi

**Tra cứu nghiệp vụ:**
```
> Chi phí thuê vận chuyển hạt bi thép từ cảng về kho
> Chi phí tiếp khách ký hợp đồng bán máy phun bi
> Lương KPI cho nhân viên kinh doanh
> Nhập khẩu máy phun bi từ Trung Quốc
```

**Kiểm tra hồ sơ:**
```
> Kiểm tra hồ sơ: Chi phí sửa chữa máy phun bi tại xưởng khách hàng
> Kiểm tra: Tạm ứng công tác phí cho kỹ thuật viên đi lắp máy ở Hải Phòng
```

---

## Ví dụ câu trả lời

**Câu hỏi:** "Chi phí thuê vận chuyển hạt bi thép cần hồ sơ gì?"

**Trả lời của AI Agent:**

```
📋 NGHIỆP VỤ: CHI PHÍ THUÊ VẬN CHUYỂN HÀNG HÓA
════════════════════════════════════════════════

📌 BẢN CHẤT NGHIỆP VỤ:
Chi phí vận chuyển hạt bi thép từ nhà cung cấp/cảng về kho INSAKO
là chi phí hợp lý được trừ khi xác định thuế TNDN.

📄 HỒ SƠ CẦN CÓ:
☐ Hợp đồng vận chuyển (nếu định kỳ/giá trị lớn)
☐ Hóa đơn GTGT từ đơn vị vận chuyển (VAT 10%)
☐ Biên bản giao nhận hàng hoặc phiếu nhập kho
☐ Lệnh điều xe hoặc phiếu yêu cầu vận chuyển nội bộ
☐ Chứng từ thanh toán (chuyển khoản nếu > 20 triệu)

⚠️ RỦI RO THUẾ:
- VAT: Không được khấu trừ nếu thanh toán tiền mặt > 20 triệu
- TNDN: Bị loại nếu không có hóa đơn hợp lệ hoặc không chứng minh
  được liên quan đến hoạt động kinh doanh

🚦 MỨC ĐỘ RỦI RO: THẤP (nếu hồ sơ đầy đủ)

✅ KHUYẾN NGHỊ: Yêu cầu đơn vị vận chuyển xuất hóa đơn điện tử
ngay khi giao hàng. Thanh toán qua chuyển khoản.
```

---

## Roadmap nâng cấp

| Giai đoạn | Tính năng | Thời gian |
|-----------|-----------|-----------|
| v1.0 | CLI cơ bản + Knowledge Base Markdown | Tháng 1 |
| v1.5 | Tích hợp Claude API / OpenAI API | Tháng 2 |
| v2.0 | SQLite + tìm kiếm ngữ nghĩa | Tháng 3 |
| v2.5 | Giao diện web (Streamlit/FastAPI) | Tháng 4 |
| v3.0 | Tích hợp Lark Base, MISA AMIS | Tháng 5-6 |
| v3.5 | ChromaDB / Supabase vector search | Tháng 7 |
| v4.0 | Multi-agent: Kế toán + Thuế + Kiểm toán nội bộ | Tháng 9 |

---

## Lưu ý pháp lý

> **QUAN TRỌNG:** Hệ thống này chỉ mang tính chất hỗ trợ tra cứu và kiểm tra sơ bộ.
> Mọi quyết định kế toán, thuế cuối cùng phải được xác nhận bởi kế toán trưởng
> và/hoặc chuyên gia thuế có chứng chỉ hành nghề.
> Cần đối chiếu với quy định pháp luật hiện hành trước khi áp dụng.

---

*Phát triển cho INSAKO – Hệ thống phun bi, phun cát công nghiệp Việt Nam*
