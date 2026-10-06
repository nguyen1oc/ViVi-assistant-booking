# Nguồn chính thức VinFast — giá bán, tên gọi và văn phong

Tài liệu này là **nguồn tham chiếu duy nhất** cho backend khi ghi giá xe, tên mẫu xe và câu chữ
hiển thị cho khách. Mọi con số và câu chữ dưới đây được trích trực tiếp từ bản lưu HTML của
vinfastauto.com, không phải do người viết tự soạn.

> **Nguyên tắc số một: KHÔNG BỊA.**
> Mẫu nào tài liệu này ghi "chưa công bố" thì backend trả rỗng và giao diện hiện "Đang cập nhật".
> Tuyệt đối không lấy giá của mẫu này gán cho mẫu khác, không làm tròn, không tự suy ra.
> Đã có tiền lệ: một lần gán cứng ba màu mặc định cho cả 14 mẫu xe khiến trang khách hiện tên màu
> bịa như thể là màu chính hãng.

---

## 1. Nguồn dữ liệu

| | |
|---|---|
| Nguồn | Bản lưu trang chi tiết sản phẩm trên `vinfastauto.com` |
| Ngày crawl | 16/08/2026 (VF 3–9) và 17/08/2026 (dòng Green, EC Van, EBus) |
| Số trang | 14 trang, mỗi trang ~2,9 MB |
| Vị trí | `~/Downloads/craw web html/` — **nằm ngoài repo**, không được commit |

**Đây là ảnh chụp tại một thời điểm.** Giá xe và chương trình ưu đãi thay đổi theo tháng. Trước
mỗi đợt phát hành, phải crawl lại và đối chiếu; đừng coi số trong file này là vĩnh viễn.

---

## 2. Bảng giá chính thức

Hai cột giá **luôn đi cùng nhau** trên trang gốc: giá ưu đãi (có dấu `*`) và giá niêm yết
(gạch ngang). Đơn vị VNĐ.

| Mẫu xe | Phiên bản | Giá ưu đãi (*) | Giá niêm yết | Nhãn gốc trên trang |
|---|---|---:|---:|---|
| VF 3 | Eco | 270.750.000 | 285.000.000 | Giá bán từ |
| VF 3 | Plus | 281.200.000 | 296.000.000 | Giá bán từ |
| VF 5 | — | 471.200.000 | 496.000.000 | Giá bán VF 5 |
| VF 6 | Eco | 613.700.000 | 646.000.000 | Giá bán từ |
| VF 6 | Plus | 664.050.000 | 699.000.000 | Giá bán từ |
| VF 7 | Eco | 703.000.000 | 740.000.000 | Giá bán từ |
| VF 7 | Plus | 788.500.000 | 830.000.000 | Giá bán từ |
| VF 7 | Plus Trần kính toàn cảnh | 807.500.000 | 850.000.000 | Giá bán từ |
| VF MPV 7 | — | 712.500.000 | 750.000.000 | Giá bán từ: |
| VF 8 | Eco | 853.100.000 | 898.000.000 | Giá bán từ |
| VF 8 | Plus | 1.025.050.000 | 1.079.000.000 | Giá bán từ |
| VF 9 | Eco | 1.280.600.000 | 1.348.000.000 | Giá bán từ |
| VF 9 | Plus | 1.452.550.000 | 1.529.000.000 | Giá bán từ |
| Minio Green | — | 178.600.000 | 188.000.000 | **Giá xe kèm pin từ** |
| Limo Green | — | 664.050.000 | 699.000.000 | **Giá kèm pin từ** |
| EC Van | — | 254.600.000 | 268.000.000 | Giá bán từ |

**Lưu ý khi đọc bảng:**

- Limo Green và VF 6 Plus trùng số (664.050.000 / 699.000.000). Đã kiểm chứng độc lập từ hai file
  HTML riêng — **trùng là ngẫu nhiên, cả hai đều đúng**, đừng "sửa" một trong hai.
- Dòng Green dùng chữ **"Giá kèm pin"**, dòng VF dùng **"Giá bán"**. Khác biệt này có ý nghĩa
  thương mại (đã gồm pin hay chưa), phải giữ nguyên chứ không đồng nhất hoá.
- VF 5 chỉ có một mức giá trên trang, không chia Eco/Plus.
- VF 7 có **ba** phiên bản, trong đó "Plus Trần kính toàn cảnh" là bản riêng chứ không phải tuỳ chọn.

### Mẫu CHƯA công bố giá

Bốn mẫu sau **không có bất kỳ con số giá nào** trên trang chính thức tại thời điểm crawl:

| Mẫu xe | Ghi chú |
|---|---|
| Nerio Green | Trang chỉ có nút "Đặt cọc", không hiện giá |
| Herio Green | Trang chỉ có nút "Đặt cọc", không hiện giá |
| EBus | Trang giới thiệu, không có khối giá |
| VF 8 Thế Hệ Mới | Trang thông tin sản phẩm, không có khối giá |

→ Backend trả `[]` hoặc `null` cho các mẫu này. Giao diện đã xử lý sẵn: hiện "Đang cập nhật".

---

## 3. Quy tắc hiển thị giá

1. **Định dạng số**: dấu chấm phân cách hàng nghìn — `270.750.000`. Không dùng dấu phẩy,
   không viết tắt "270,75 triệu".
2. **Đơn vị**: `VNĐ` (không phải "VND", không phải "đ").
3. **Dấu sao**: giá ưu đãi luôn kèm `*`, và **bắt buộc** đi kèm ghi chú:

   > (*) Mức giá ưu đãi mang tính chất tham khảo. Chương trình áp dụng theo điều khoản & điều kiện.

   Bỏ dòng này là sai lệch thông tin thương mại. Nếu giao diện hiện giá ưu đãi mà không có chỗ
   đặt ghi chú, thì hiện giá niêm yết thay vì bỏ ghi chú.
4. **Chữ dẫn**: dùng "Giá bán từ" (có chữ *từ*), không dùng "Giá:" hay "Chỉ từ".
5. **Giá niêm yết** hiển thị gạch ngang, đặt dưới giá ưu đãi.

---

## 4. Tên mẫu xe chuẩn

Viết đúng theo trang gốc. Sai một dấu cách là sai tên thương hiệu.

| Đúng | Sai thường gặp |
|---|---|
| `VinFast VF 3` | VinFast VF3, Vinfast VF 3 |
| `VinFast VF 5` | VF5 |
| `VinFast VF 6` | VF6 |
| `VinFast VF 7` | VF7 |
| `VinFast VF MPV 7` | VF 7 MPV, VF MPV7 |
| `VinFast VF 8` | VF8 |
| `VinFast VF 9` | VF9 |
| `VinFast VF 8 Thế Hệ Mới` | VF8 All New, VF 8 thế hệ mới |
| `VinFast Minio Green` | Minio, MinioGreen |
| `VinFast Limo Green` | Limo |
| `VinFast Herio Green` | Herio |
| `VinFast Nerio Green` | Nerio |
| `VinFast EC Van` | ECVan, EC-Van |
| `VinFast EBus` | E-Bus, Ebus |

**Quy tắc chung:** luôn có dấu cách giữa `VF` và số. Thương hiệu viết `VinFast` — chữ **F hoa**,
không phải "Vinfast". Phiên bản viết hoa chữ đầu: `Eco`, `Plus`.

---

## 5. Văn phong và câu chữ

### 5.1. Nhãn nút chuẩn

Trích theo tần suất xuất hiện trên 14 trang:

| Nhãn | Dùng khi |
|---|---|
| `Đăng ký lái thử` | Mời đặt lịch lái thử — **đây là nhãn của dự án mình** |
| `Đặt cọc` / `Đặt cọc ngay` | Chuyển sang luồng đặt cọc mua xe |
| `Nhận báo giá & ưu đãi mới nhất` | Form thu thập thông tin khách |
| `Thông tin sản phẩm` | Mở trang chi tiết xe |
| `Dự toán chi phí lăn bánh` | Công cụ tính chi phí |
| `So sánh xe` | Công cụ so sánh |
| `Tải brochure` | Tải tài liệu PDF |
| `Nhận tư vấn` / `Đăng ký tư vấn` | Yêu cầu tư vấn viên liên hệ |

**Viết hoa:** trang gốc dùng lẫn lộn cả `TẢI BROCHURE` lẫn `Tải brochure`. Dự án mình
**thống nhất viết hoa chữ đầu**, không viết hoa toàn bộ — viết hoa toàn bộ gây cảm giác quảng cáo.

### 5.2. Giọng văn

Đọc qua mô tả 14 mẫu xe, VinFast dùng một giọng ổn định:

- **Câu ngắn, nhiều mệnh đề song song.** Ví dụ có thật:
  *"Vận tải đa năng, tiện dụng, sinh lời"* · *"Xe nhỏ, giá trị lớn"* ·
  *"Lái xanh, lãi đỉnh"* · *"Cầm lái với đam mê"*
- **Lợi ích trước, thông số sau.** Tiêu đề nói khách được gì, con số để ở bảng thông số.
- **Không dùng ngôi thứ nhất.** Không có "chúng tôi cam kết"; câu văn hướng vào sản phẩm hoặc
  vào khách ("Tùy chọn cho ngân sách của bạn").
- **Không dùng emoji, không dùng dấu chấm than.** Ngoại lệ duy nhất tìm thấy là thông báo hệ thống
  "Đăng ký thành công!".
- **Từ khoá lặp lại xuyên suốt:** *xanh, thông minh, tiết kiệm, tiên phong, êm ái, mạnh mẽ,
  tinh tế, vượt trội*.

Ví dụ mô tả gốc để đối chiếu văn phong:

> Xe điện VinFast VF 5 thiết kế trẻ trung, cá tính và phối màu nội ngoại thất độc đáo, trang bị
> những công nghệ hỗ trợ lái tiên tiến, trợ lý ảo thông minh, bảo hành 7 năm.

> Minio Green – xe điện mini 4 chỗ nhỏ gọn, tiết kiệm chi phí, phù hợp di chuyển đô thị và kinh
> doanh dịch vụ.

> Đặt cọc xe điện VinFast VF 6 chỉ 30 triệu đồng, chi phí vận hành tiết kiệm, bảo hành xe 7 năm,
> thiết kế tinh tế, động cơ mạnh mẽ, là lựa chọn lý tưởng cho gia đình trẻ.

### 5.3. Tên khối nội dung chuẩn

Dùng lại đúng chữ của VinFast thay vì tự đặt tên khác:

`Ngoại thất` · `Nội thất` · `Công nghệ` · `Vận hành` · `Thông số kỹ thuật` ·
`Thông số sản phẩm` · `Tùy chọn cho ngân sách của bạn.` ·
`So sánh giữa xe VinFast {tên xe} và xe động cơ đốt trong`

### 5.4. Ghi chú pháp lý bắt buộc

Những câu này phải xuất hiện nguyên văn khi hiển thị dữ liệu tương ứng:

| Khi hiển thị | Ghi chú bắt buộc |
|---|---|
| Giá ưu đãi | (*) Mức giá ưu đãi mang tính chất tham khảo. Chương trình áp dụng theo điều khoản & điều kiện. |
| Công cụ tính chi phí | (*) Lưu ý: Các thông số, đơn giá và giả định sử dụng để tính chi phí nhiên liệu có thể thay đổi. |
| Màu xe bản tiền thương mại | (*) Lưu ý: Màu sắc của xe phiên bản tiền thương mại. Màu sắc phiên bản thương mại có thể thay đổi. |
| Quãng đường WLTP | (*) Tiêu chuẩn WLTP, phiên bản Eco pin CATL |

---

## 6. Chính sách bán hàng

### Tiền đặt cọc

| Mẫu xe | Đặt cọc |
|---|---|
| VF 3 | 15.000.000 VNĐ |
| VF 6 | 30.000.000 VNĐ (theo mô tả trang) |
| VF 9 | 50.000.000 VNĐ |

Các mẫu khác không ghi rõ số tiền cọc trên trang.

### Thuê pin (chỉ VF 3 có bảng công khai)

| Quãng đường/tháng | Giá thuê |
|---|---|
| Dưới 1.500 km | 1.100.000 VNĐ/tháng |
| 1.500 – 2.500 km | 1.400.000 VNĐ/tháng |
| Trên 2.500 km | 3.000.000 VNĐ/tháng |

*Ghi chú: khối này nằm trong phần bị comment trên trang gốc — có thể đã ngừng áp dụng.
Phải xác nhận lại với phòng kinh doanh trước khi hiển thị cho khách.*

### Bảo hành

| Loại | Thời hạn |
|---|---|
| Xe mới (xe cá nhân) | 7 năm hoặc 160.000 km |
| Xe dùng mục đích thương mại | 3 năm hoặc 100.000 km |
| Nerio Green | 10 năm |

### Miễn phí sạc

- Dòng VF cá nhân: *"miễn phí sạc từ V-Green, áp dụng kèm điều kiện và điều khoản"*
- Dòng Green (dịch vụ): *"miễn phí sạc từ V-Green và Green SM, áp dụng kèm điều kiện và điều khoản"*
- VF 8: *"Miễn phí sạc 2 năm tại các trụ VinFast"*
- Mốc kết thúc chính sách miễn phí sạc: **10/02/2026** (dùng trong công cụ dự toán chi phí)

---

## 7. Thông số kỹ thuật

Chỉ liệt kê những mẫu trích được sạch từ bản lưu. Các mẫu còn lại (VF 6, VF 7, VF 8, VF 9,
VF MPV 7, Nerio Green, Herio Green, EBus) có bảng thông số dựng bằng JavaScript nên **không đọc
được từ HTML tĩnh** — cần crawl lại bằng trình duyệt thật nếu muốn.

### VF 3

| Thông số | Giá trị |
|---|---|
| Động cơ | 01 Motor |
| Công suất tối đa | 30 kW |
| Mô men xoắn cực đại | 110 Nm |
| Quãng đường một lần sạc đầy | 215 km |
| Thời gian nạp pin nhanh nhất | 36 phút (10% – 70%) |
| Dẫn động | RWD/Cầu sau |

### VF 5

| Thông số | Giá trị |
|---|---|
| Dài × rộng × cao | 3.967 × 1.723 × 1.579 mm |
| Dung lượng pin khả dụng | 37,23 kWh |
| La-zăng | Hợp kim 17 inch |
| Tiêu thụ điện công khai | 13 kWh/100 km |
| Số ghế | 5 ghế |
| Nạp pin nhanh nhất (10%–70%) | 33 phút |
| Túi khí | 6 túi khí |

### VF 8 Thế Hệ Mới

| Thông số | Giá trị |
|---|---|
| Dài × rộng × cao | 4.701 × 1.872 × 1.670 mm |
| Số ghế | 5 ghế |
| Dung lượng pin khả dụng | 60,13 kWh |
| Nạp pin nhanh nhất (10%–70%) | Dưới 30 phút |
| Mâm xe | 19 inch |
| Màn hình trung tâm | 12,9 inch |
| Ghế lái | Chỉnh điện 6 hướng, nhớ vị trí |

### Minio Green

| Thông số | Giá trị |
|---|---|
| Chiều dài cơ sở | 2.065 mm |
| Khoảng sáng gầm | 166,3 mm |
| Công suất tối đa | 30 kW |
| Mô men xoắn cực đại | 65 Nm |
| Quãng đường (NEDC) | 210 km/lần sạc đầy |
| Dung lượng pin khả dụng | 18,3 kWh |
| Công suất sạc tối đa | ≥24 kW |
| Dẫn động | RWD/Cầu sau |
| Chế độ lái | Eco/Normal |
| Treo trước/sau | MacPherson/MacPherson |
| Phanh trước/sau | Đĩa/Tang trống |
| La-zăng | 13 inch |
| Đèn trước | LED |

### EC Van

| Thông số | Giá trị |
|---|---|
| Dài × rộng × cao | 3.767 × 1.680 × 1.790 mm |
| Chiều dài cơ sở | 2.520 mm |
| Khoảng sáng gầm không tải | 165 mm |
| Bán kính quay vòng | 5,1 m |
| Dung tích khoang hàng | 2,6 m³ |
| Số chỗ ngồi | 02 chỗ |
| Công suất tối đa | 30 kW |
| Mô men xoắn cực đại | 110 Nm |
| Quãng đường (NEDC) | 175 km/sạc đầy |
| Dung lượng pin khả dụng | 18,3 kWh |
| Sạc nhanh DC tối đa | 24,2 kW |
| Nạp pin nhanh nhất | 42 phút (10% – 70%) |

### Limo Green

| Thông số | Giá trị |
|---|---|
| Dài × rộng × cao | 4.740 × 1.872 × 1.729 mm |
| Chiều dài cơ sở | 2.840 mm |
| Khoảng sáng gầm xe | 180 mm |
| Công suất tối đa | 150 kW |
| Mô men xoắn cực đại | 280 Nm |
| Quãng đường (NEDC) | 450 km/lần sạc đầy |
| Dung lượng pin khả dụng | 60,13 kWh |
| Sạc nhanh DC tối đa | 80 kW |
| Nạp pin nhanh nhất | 30 phút (10% – 70%) |
| Dẫn động | FWD/Cầu trước |
| Chế độ lái | Eco/Normal |
| La-zăng | 18 inch |
| Treo trước/sau | MacPherson/Đa liên kết |

> **Cảnh báo cho người crawl lần sau:** bảng thông số của Limo Green xếp theo thứ tự
> **giá trị → đơn vị → nhãn**, ngược với Minio Green và EC Van (nhãn → giá trị). Đọc máy móc theo
> cặp liền nhau sẽ ra kết quả sai lệch một nhịp: lần đầu trích tự động đã cho ra "công suất 180 kW"
> và "mô men 450 Nm", trong khi số đúng là 150 kW và 280 Nm. Luôn mở lại HTML đối chiếu bằng mắt.

---

## 8. Những gì nguồn này KHÔNG có

Ghi rõ để backend không đi tìm nhầm chỗ, và không tự bịa ra:

| Thiếu | Tình trạng |
|---|---|
| **Tên màu xe chính thức** | Không nằm dạng text trong HTML — do JavaScript render. Muốn lấy phải crawl bằng trình duyệt thật. Hiện `frontend/src/data/vehicle-colors.js` đang vá tạm 5 mẫu bằng tên chép tay từ vinfast.vn. |
| Giá 4 mẫu (Nerio, Herio, EBus, VF 8 Thế Hệ Mới) | Trang gốc không công bố |
| Thông số 8 mẫu | Bảng dựng bằng JavaScript |
| Tiền cọc phần lớn mẫu | Chỉ VF 3, VF 6, VF 9 ghi rõ |

---

## 9. Cách backend dùng tài liệu này

1. **Nhập giá** vào `backend/src/services/site_catalog.py` theo đúng bảng mục 2, giữ cả hai cột
   (ưu đãi và niêm yết) chứ không chỉ một.
2. **Không gán giá trị mặc định** cho mẫu thiếu dữ liệu — trả `[]` / `null`.
3. **Câu chữ hiển thị** lấy từ mục 5, đừng tự viết lại cho "hay hơn".
4. **Ghi chú pháp lý** ở mục 5.4 đi kèm dữ liệu tương ứng, không được lược bỏ.
5. Khi crawl lại đợt mới, **cập nhật ngày ở mục 1** để người sau biết dữ liệu cũ tới đâu.

Xem thêm: [`frontend/BACKEND_TODO.md`](../../frontend/BACKEND_TODO.md) — danh sách việc backend cần
làm, trong đó có mục màu xe và mục danh mục trả `colorOptions`.
