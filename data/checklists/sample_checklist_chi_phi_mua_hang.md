# CHECKLIST: CHI PHÍ MUA HÀNG HÓA & VẬT TƯ

> Áp dụng cho: Mua hạt bi thép, phụ tùng máy phun bi, vật tư phụ trợ, văn phòng phẩm
> Cập nhật: 2026-07-01 | AI Agent Kế toán INSAKO

---

## A. MUA HÀNG THÔNG THƯỜNG TRONG NƯỚC

### Hồ sơ tối thiểu (BẮT BUỘC)

- [ ] **Hóa đơn GTGT điện tử** hợp lệ (tên, địa chỉ, MST người mua đúng INSAKO)
- [ ] **Phiếu nhập kho** (mã hàng, số lượng, đơn giá, tổng giá – thủ kho ký)
- [ ] **Chứng từ thanh toán** (chuyển khoản nếu > 20 triệu)

### Hồ sơ nên có (BỔ SUNG)

- [ ] Hợp đồng mua bán (nếu định kỳ, nhiều đợt hoặc > 20 triệu)
- [ ] Biên bản kiểm nhận hàng hóa (nếu cần kiểm tra chất lượng)
- [ ] Phiếu yêu cầu mua hàng nội bộ (Purchase Request – PR)
- [ ] Báo giá từ ít nhất 3 nhà cung cấp (nếu giá trị lớn)
- [ ] Phê duyệt mua hàng của Kế toán trưởng / Giám đốc

---

## B. KIỂM TRA HÓA ĐƠN

### Kiểm tra thông tin trên hóa đơn

- [ ] Tên công ty người bán đúng, đầy đủ?
- [ ] MST người bán hợp lệ (kiểm tra trên thuedientu.gdt.gov.vn)?
- [ ] Tên công ty người mua = "Công ty CP Đầu tư và Thương mại Thế Nam"?
- [ ] MST người mua đúng?
- [ ] Địa chỉ người mua đúng địa chỉ đăng ký kinh doanh?
- [ ] Mô tả hàng hóa/dịch vụ rõ ràng, khớp thực tế?
- [ ] Đơn vị tính, số lượng, đơn giá, thành tiền đúng?
- [ ] Thuế suất VAT đúng (0%/8%/10% tùy loại hàng)?
- [ ] Số tiền VAT = Thành tiền × Thuế suất?
- [ ] Hóa đơn có chữ ký điện tử hợp lệ (trạng thái "Hợp lệ" trên cổng CQT)?
- [ ] Ngày xuất hóa đơn phù hợp với ngày giao hàng/nghiệm thu?

### Kiểm tra tình trạng hóa đơn

- [ ] Không phải hóa đơn của doanh nghiệp ngừng hoạt động / bỏ trốn?
- [ ] Tra cứu thông tin người bán tại: tracuunnt.gdt.gov.vn
- [ ] Hóa đơn chưa bị hủy bỏ hoặc điều chỉnh?

---

## C. KIỂM TRA ĐIỀU KIỆN KHẤU TRỪ VAT

- [ ] Hóa đơn GTGT hợp lệ (như kiểm tra ở mục B)?
- [ ] Thanh toán chuyển khoản nếu giá trị hàng hóa > 20 triệu đồng?
- [ ] Hàng hóa/dịch vụ dùng cho hoạt động chịu thuế của INSAKO?
- [ ] Không phải hàng hóa/dịch vụ thuộc danh mục không được khấu trừ?
- [ ] Kê khai trong kỳ tính thuế hoặc kỳ tiếp theo (không quá 6 tháng)?

> **Lưu ý INSAKO:** Nếu mua hàng phục vụ cả hoạt động chịu thuế và không chịu thuế → phải phân bổ VAT được khấu trừ.

---

## D. KIỂM TRA ĐIỀU KIỆN CHI PHÍ HỢP LÝ (TNDN)

- [ ] Chi phí thực tế phát sinh, gắn với hoạt động sản xuất kinh doanh?
- [ ] Có hóa đơn hợp lệ hoặc chứng từ thay thế theo quy định?
- [ ] Thanh toán chuyển khoản (nếu > 20 triệu)?
- [ ] Hàng hóa đã nhập kho, sử dụng cho mục đích kinh doanh (không phải cá nhân)?
- [ ] Không thuộc danh mục chi phí không được trừ (quà biếu cá nhân, phạt, v.v.)?

---

## E. HẠCH TOÁN MẪU

### Khi nhận hàng vào kho
```
Nợ TK 152/153/156  (Vật liệu/Công cụ/Hàng hóa) : Giá chưa VAT
Nợ TK 1331         (VAT được khấu trừ)          : Tiền VAT
  Có TK 331        (Phải trả người bán)          : Tổng tiền HĐ
```

### Khi thanh toán
```
Nợ TK 331          (Phải trả người bán)          : Số tiền TT
  Có TK 112        (Tiền gửi ngân hàng)           : Số tiền TT
```

### Khi xuất kho dùng cho sản xuất/dịch vụ
```
Nợ TK 621/627/641/642  (Chi phí tương ứng)       : Giá xuất kho
  Có TK 152/153/156    (Kho tương ứng)            : Giá xuất kho
```

---

## F. CÁC LỖI SAI THƯỜNG GẶP

| Lỗi | Hậu quả | Cách tránh |
|-----|---------|------------|
| Hóa đơn ghi sai tên/MST người mua | Không được khấu trừ VAT, bị loại chi phí | Kiểm tra kỹ trước khi yêu cầu xuất HĐ |
| Thanh toán tiền mặt > 20 triệu | Mất quyền khấu trừ VAT, bị loại chi phí TNDN | Luôn chuyển khoản cho khoản > 20 triệu |
| Nhập kho chưa có HĐ | Rủi ro hạch toán sai kỳ | Chờ có HĐ mới nhập kho kế toán |
| Không có phiếu nhập kho | Không chứng minh được hàng đã nhận | Luôn làm phiếu nhập kho khi nhận hàng |
| Mua từ DN bỏ trốn | Bị loại toàn bộ, truy thu VAT + phạt | Tra cứu MST người bán trước khi mua |

---

## G. DANH MỤC HÀNG HÓA ĐẶC THÙ INSAKO

| Hàng hóa | Thuế suất VAT | Ghi chú |
|----------|--------------|---------|
| Hạt bi thép (sản xuất trong nước) | 10% | Hàng hóa thông thường |
| Máy phun bi nhập khẩu | 10% | VAT nhập khẩu + VAT nội địa khi bán |
| Phụ tùng máy phun bi | 10% | |
| Dịch vụ bảo trì, sửa chữa | 10% | |
| Dịch vụ lắp đặt thiết bị | 10% | |

---

> ⚠️ *Cần đối chiếu với quy định pháp luật hiện hành và tư vấn chuyên gia trước khi áp dụng.*
