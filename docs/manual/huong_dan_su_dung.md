# HƯỚNG DẪN SỬ DỤNG CHI TIẾT – INSAKO TAX AGENT

## 1. Cài đặt lần đầu (5 phút)

### Bước 1: Kiểm tra Python
```bash
python --version
# Cần: Python 3.9 trở lên
```

### Bước 2: Tạo môi trường ảo (khuyến nghị)
```bash
cd insako-tax-agent
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### Bước 3: Cài thư viện
```bash
# Phiên bản cục bộ (không cần API)
pip install anthropic

# Hoặc cài tất cả
pip install -r requirements.txt
```

### Bước 4: Cấu hình

Sao chép file cấu hình:
```bash
copy config.example.json config.json
```

Mở `config.json` và chỉnh sửa:
```json
{
  "ai": {
    "api_key": "sk-ant-api03-YOUR_REAL_KEY_HERE"
  }
}
```

> **Lấy API key:** Đăng nhập https://console.anthropic.com → API Keys → Create Key

### Bước 5: Chạy chương trình
```bash
python main.py
```

---

## 2. Sử dụng từng chức năng

### Chức năng 1: Tra cứu nghiệp vụ

Dùng khi bạn cần hiểu một nghiệp vụ mới hoặc cần xác nhận cách xử lý.

**Câu hỏi mẫu:**
```
Chi phí thuê kỹ thuật viên tự do lắp đặt máy phun bi tại Hải Phòng,
trả 5 triệu đồng tiền mặt, không ký hợp đồng
```

**AI sẽ trả lời:**
- Bản chất nghiệp vụ
- Hồ sơ cần có (hợp đồng dịch vụ, biên bản nghiệm thu, v.v.)
- Điều kiện khấu trừ VAT
- Rủi ro TNCN (trả cho cá nhân > 2 triệu → khấu trừ 10%)
- Cách hạch toán

---

### Chức năng 2: Kiểm tra hồ sơ

Dùng trước khi hạch toán một khoản chi cụ thể.

**Mô tả đầu vào tốt:**
```
Khoản chi: Mua 5 tấn hạt bi thép W47 từ Công ty ABC
Số tiền: 120.000.000 đ (đã VAT)
Hình thức TT: Chuyển khoản
Hồ sơ hiện có: Hóa đơn VAT, phiếu nhập kho
Còn thiếu: Hợp đồng
```

---

### Chức năng 3: Tạo checklist

Chọn từ danh sách nhanh hoặc nhập tên nghiệp vụ:
- "Nhập khẩu máy phun bi từ Trung Quốc"
- "Ký hợp đồng bảo trì máy với Vingroup"
- "Chi phí hoa hồng cho đại lý bán máy"

---

### Chức năng 4: Ghi nhận lỗi

Thực hiện theo 5 bước trên màn hình. Nên ghi nhận ngay khi phát hiện.

**Thông tin quan trọng nhất:**
- Mô tả sai sót rõ ràng (ai làm gì sai)
- Nguyên nhân gốc rễ (tại sao xảy ra)
- Biện pháp phòng ngừa cụ thể

---

### Chức năng 6: Xuất báo cáo

Báo cáo xuất ra thư mục `outputs/` dạng file Markdown.
Có thể dùng để:
- Báo cáo lên Giám đốc / Kế toán trưởng
- Chuẩn bị cho kỳ quyết toán thuế
- Lập kế hoạch cải thiện quy trình

---

## 3. Mẹo sử dụng hiệu quả

### Câu hỏi chi tiết → Câu trả lời chính xác hơn
❌ "Chi phí vận chuyển cần gì?"
✅ "Chi phí thuê xe tải chở 10 tấn hạt bi thép từ cảng Hải Phòng về kho Hà Nội,
   đơn vị vận chuyển là cá nhân có xe, thanh toán 8 triệu tiền mặt"

### Cung cấp đầy đủ bối cảnh
- Số tiền cụ thể
- Đối tượng nhận tiền (công ty hay cá nhân)
- Hình thức thanh toán
- Hồ sơ đã có

### Kiểm tra lại
AI không phải chuyên gia thuế được cấp phép. Luôn xác nhận lại với:
- Kế toán trưởng cho quyết định lớn
- Chuyên gia thuế khi có rủi ro cao
- Văn bản pháp luật hiện hành

---

## 4. Thêm nội dung vào Knowledge Base

### Thêm quy định nội bộ mới

Tạo file `.md` trong `data/knowledge_base/`:
```
data/knowledge_base/quy_dinh_chi_phi_khach_hang_2026.md
```

### Thêm checklist mới

Tạo file trong `data/checklists/` theo mẫu `data/templates/checklist_template.md`.

### Thêm case lỗi

Dùng Chức năng 4 trong CLI, hoặc thêm thủ công vào `data/tax_cases/cases_db.json`.

---

## 5. Xử lý sự cố

### "Không kết nối được Claude API"
→ Kiểm tra API key trong `config.json`
→ Kiểm tra kết nối internet
→ Dùng chế độ cục bộ (vẫn tra cứu được KB)

### "Không tìm thấy thông tin trong KB"
→ Thêm tài liệu liên quan vào `data/knowledge_base/`
→ Dùng từ khóa tiếng Việt không dấu hoặc có dấu

### Chương trình không khởi động
→ Kiểm tra Python version: `python --version`
→ Kiểm tra đang ở đúng thư mục: `cd insako-tax-agent`
→ Kiểm tra file config.json tồn tại
