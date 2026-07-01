# MẪU BÚT TOÁN KẾ TOÁN INSAKO

> Hệ thống tài khoản theo Thông tư 200/2014/TT-BTC
> Cập nhật: 2026-07-01

---

## CÁC BÚT TOÁN THƯỜNG GẶP TẠI INSAKO

### 1. MUA HÀNG HÓA (hạt bi thép, phụ tùng)

**Khi nhận hàng:**
```
Nợ TK 156    Hàng hóa (giá chưa VAT)          : xxx
Nợ TK 1331   Thuế GTGT được khấu trừ          : xxx
  Có TK 331  Phải trả người bán                : xxx
```

**Khi thanh toán:**
```
Nợ TK 331    Phải trả người bán                : xxx
  Có TK 112  Tiền gửi ngân hàng               : xxx
```

---

### 2. NHẬP KHẨU MÁY MÓC

**Khi thông quan (phát sinh thuế NK + VAT NK):**
```
Nợ TK 2111   Máy móc thiết bị (giá CIF)       : xxx
Nợ TK 2111   Máy móc thiết bị (thuế NK)       : xxx  ← cộng vào nguyên giá
Nợ TK 1331   VAT nhập khẩu được khấu trừ      : xxx
  Có TK 333  Thuế và các khoản phải nộp NN    : xxx  ← thuế NK + VAT NK
  Có TK 331  Phải trả người bán nước ngoài    : xxx  ← giá CIF
```

**Nộp thuế NK + VAT NK:**
```
Nợ TK 333    Thuế và các khoản phải nộp NN    : xxx
  Có TK 112  Tiền gửi ngân hàng               : xxx
```

**Chi phí vận chuyển về kho (cộng vào nguyên giá TSCĐ):**
```
Nợ TK 2111   Máy móc thiết bị                 : xxx  ← giá chưa VAT
Nợ TK 1331   VAT được khấu trừ               : xxx
  Có TK 112  Tiền gửi ngân hàng               : xxx
```

---

### 3. CHI PHÍ LƯƠNG

**Hạch toán lương hàng tháng:**
```
Nợ TK 6411   Lương nhân viên kinh doanh       : xxx
Nợ TK 6421   Lương nhân viên quản lý          : xxx
Nợ TK 6221   Lương nhân viên kỹ thuật/dịch vụ: xxx
  Có TK 334  Phải trả người lao động          : xxx  ← lương thực lĩnh
  Có TK 3383 Bảo hiểm xã hội (NLĐ đóng)     : xxx
  Có TK 3384 Bảo hiểm y tế (NLĐ đóng)       : xxx
  Có TK 3385 Bảo hiểm thất nghiệp (NLĐ đóng): xxx
  Có TK 3335 Thuế TNCN khấu trừ tại nguồn   : xxx
```

**BHXH phần chủ sử dụng lao động đóng:**
```
Nợ TK 6411/6421/6221  Chi phí BHXH chủ SLĐ  : xxx
  Có TK 3383  BHXH phần chủ đóng            : xxx
  Có TK 3384  BHYT phần chủ đóng            : xxx
  Có TK 3385  BHTN phần chủ đóng            : xxx
```

**Thanh toán lương:**
```
Nợ TK 334    Phải trả người lao động          : xxx
  Có TK 112  Tiền gửi ngân hàng               : xxx
```

---

### 4. TẠM ỨNG & HOÀN ỨNG

**Xuất tiền tạm ứng:**
```
Nợ TK 141    Tạm ứng                           : xxx
  Có TK 111  Tiền mặt                          : xxx
```

**Hoàn ứng (ghi nhận chi phí):**
```
Nợ TK 6xx   Chi phí (phù hợp)                 : xxx
Nợ TK 1331  VAT đầu vào (nếu có HĐ VAT)       : xxx
  Có TK 141 Tạm ứng                            : xxx
  Có TK 111 Tiền mặt (nộp lại phần thừa)      : xxx
```

---

### 5. DOANH THU BÁN MÁY

**Ghi nhận doanh thu:**
```
Nợ TK 131    Phải thu khách hàng              : xxx  ← tổng HĐ (đã VAT)
  Có TK 511  Doanh thu bán hàng hóa           : xxx  ← giá chưa VAT
  Có TK 3331 Thuế GTGT phải nộp              : xxx
```

**Giá vốn hàng bán:**
```
Nợ TK 632    Giá vốn hàng bán                 : xxx
  Có TK 156  Hàng hóa                         : xxx
```

**Khi khách hàng thanh toán:**
```
Nợ TK 112    Tiền gửi ngân hàng               : xxx
  Có TK 131  Phải thu khách hàng              : xxx
```

---

### 6. DOANH THU DỊCH VỤ (Lắp đặt, Bảo trì, Sửa chữa)

**Ghi nhận doanh thu dịch vụ (khi nghiệm thu):**
```
Nợ TK 131    Phải thu khách hàng              : xxx
  Có TK 511  Doanh thu dịch vụ               : xxx  ← VAT 10%
  Có TK 3331 Thuế GTGT đầu ra               : xxx
```

**Chi phí dịch vụ (nhân công kỹ thuật, vật tư, vận chuyển):**
```
Nợ TK 627    Chi phí sản xuất chung (dịch vụ): xxx
  Có TK 334/152/112...                        : xxx
```

---

### 7. TÀI SẢN CỐ ĐỊNH

**Mua TSCĐ:**
```
Nợ TK 211    TSCĐ hữu hình                    : xxx  ← giá chưa VAT
Nợ TK 1332   VAT TSCĐ được khấu trừ          : xxx
  Có TK 331  Phải trả người bán               : xxx
```

**Khấu hao hàng tháng:**
```
Nợ TK 6274/6421/6411  Chi phí khấu hao       : xxx
  Có TK 214  Hao mòn lũy kế TSCĐ            : xxx
```

---

### 8. TIẾP KHÁCH

```
Nợ TK 6421   Chi phí quản lý – tiếp khách    : xxx  ← giá chưa VAT
Nợ TK 1331   VAT đầu vào                     : xxx
  Có TK 112  Tiền gửi ngân hàng / TK 111     : xxx
```

> Lưu ý: Theo dõi riêng TK tiếp khách để kiểm soát không vượt 15% tổng chi phí được trừ

---

### 9. TRÍCH LẬP DỰ PHÒNG BẢO HÀNH

```
Nợ TK 641    Chi phí bán hàng (dự phòng BH)  : xxx
  Có TK 352  Dự phòng phải trả               : xxx
```

**Khi thực tế phát sinh chi phí bảo hành:**
```
Nợ TK 352    Dự phòng phải trả               : xxx
  Có TK 334/152/112...  (Chi phí thực tế)    : xxx
```

---

## GHI CHÚ QUAN TRỌNG

1. **TK 1331 vs 1332:** Dùng 1331 cho hàng hóa, vật tư; dùng 1332 cho TSCĐ
2. **Ngưỡng tiền mặt:** > 20 triệu phải chuyển khoản để được khấu trừ VAT
3. **Kỳ kế toán:** Ghi nhận theo nguyên tắc dồn tích (accrual basis)
4. **Ngoại tệ:** Quy đổi theo tỷ giá NHNN ngày phát sinh giao dịch

> ⚠️ *Cần đối chiếu với Thông tư 200 và các văn bản hiện hành. Các bút toán này mang tính tham khảo.*
