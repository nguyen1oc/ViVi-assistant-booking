# styles/ — style của toàn bộ website

Trước 18/08/2026 tất cả nằm trong một file `index.css` dài **13.328 dòng**. Không ai mở nổi,
nên không ai dám sửa. Nay tách thành 25 file theo màn hình và theo khối.

`src/index.css` giờ **không còn quy tắc CSS nào** — nó chỉ là bảng mục lục gồm 25 dòng `@import`.

---

## Luật quan trọng nhất: THỨ TỰ

CSS ăn theo thứ tự. Hai quy tắc cùng độ đặc hiệu thì **quy tắc đứng sau thắng**. Cả 25 file
này được cắt ra giữ nguyên trình tự cũ, nên:

- **Đảo thứ tự các dòng `@import` trong `index.css` = đổi giao diện.** Đừng sắp xếp lại cho
  "gọn mắt".
- Thêm file mới thì thêm vào **cuối** danh sách, trừ khi biết chắc nó phải chen vào giữa.
- Nhiều file cuối danh sách (`15-catalogue-2026`, `16-legibility`, `24-motion-3d`,
  `25-calendar-success`) cố tình **ghi đè** những file trước đó. Đó là chủ ý, không phải rác.

Cách kiểm tra chắc chắn không làm hỏng gì sau khi sửa:

```bash
cd frontend && npm run build
```

rồi so file `dist/assets/index-*.css` với bản trước. Lúc tách file này, kết quả build
**giống hệt từng byte** (235.365 byte, hash không đổi) — đó là cách chứng minh không đổi UI.

---

## Tìm style của một khối ở đâu

| Bạn đang sửa gì | Mở file |
|---|---|
| Biến màu, cỡ chữ, bo góc, reset, nút cơ bản | `01-foundation.css` |
| Thanh menu trên cùng, menu mobile | `02-navigation.css` |
| Hero trang chủ, dải chữ chạy | `03-home-hero.css` |
| Dải mẫu xe trang chủ, thẻ xe, chấm màu | `04-vehicle-rail.css` |
| Bento sở hữu, chương công nghệ, cảm nhận, CTA cuối trang | `05-home-sections.css` |
| Trang chi tiết xe: hero, thông số, thư viện ảnh, bảng chọn màu | `06-vehicle-detail.css` |
| Bong bóng chat ViVi, avatar, trang `/agent` | `07-agent.css` |
| Luồng đặt lịch: bố cục, biểu mẫu, danh sách khung giờ | `08-booking-core.css` |
| Breakpoint dùng chung toàn site | `09-responsive.css` |
| Studio đặt lịch: thanh công cụ, lịch đã đặt, panel xe bên trái | `10-booking-studio.css` |
| Khối upsell 3 mẫu xe, nhóm nút gợi ý của ViVi | `11-booking-upsell.css` |
| Popup chọn giờ / huỷ / đổi lịch / chọn xe, phiếu lịch | `12-booking-modals.css` |
| Màn đặt lịch thành công (hai cột) | `13-booking-success.css` |
| Hero một ảnh của trang xe, lời mời lái thử | `14-detail-hero.css` |
| Tinh chỉnh danh mục và media bản 2026 | `15-catalogue-2026.css` |
| Header sticky, logo, độ đọc, avatar ViVi | `16-legibility.css` |
| Bản đồ showroom, popup xác nhận khung giờ | `17-map-slots.css` |
| Trang hậu mãi, pin, trạm sạc | `18-ownership.css` |
| Riêng trang `/charging` | `19-charging.css` |
| Các chương hình ảnh mới của trang chủ | `20-home-chapters.css` |
| Băng báo lỗi khi backend chưa sẵn sàng | `21-fallback-states.css` |
| Ghi đè thư viện bản đồ Leaflet | `22-leaflet.css` |
| Khối Lạc Hồng, cảnh "xe tiến ra" | `23-lachong.css` |
| Chuyển động điện ảnh, sân khấu model 3D `.glb` | `24-motion-3d.css` |
| Lịch tuần, phiếu thành công, hướng dẫn sau đặt lịch | `25-calendar-success.css` |

Không chắc? Tìm thẳng theo tên class:

```bash
grep -rn "booking-upsell" frontend/src/styles/
```

Mỗi file đều ghi ở đầu nó tương ứng dòng bao nhiêu của `index.css` cũ, nên đối chiếu với
lịch sử git trước ngày 18/08/2026 vẫn ra.

---

## Việc backend cần làm (liên quan tới những gì hiện trên màn hình)

Danh sách đầy đủ nằm ở **[`../../BACKEND_TODO.md`](../../BACKEND_TODO.md)**. Đây là những mục
mà thiếu chúng thì giao diện hiện sai hoặc hiện chỗ trống:

| Việc | Hậu quả đang thấy | Style liên quan |
|---|---|---|
| Bỏ 3 màu mặc định gán cứng trong `site_catalog.py` | 14 mẫu xe hiện cùng 3 chấm màu trắng/đen/xanh, sai tên màu | `04-vehicle-rail.css` |
| Publish màu thật cho 8/14 mẫu còn lại | `vf6`, `vf-mpv-7`, `ebus` hiện "Đang cập nhật" | `04-vehicle-rail.css`, `06-vehicle-detail.css` |
| `GET /vehicles` trả `colorOptions` thật | Frontend phải gọi thêm 1 request cho từng xe | `04-vehicle-rail.css` |
| Sửa đuôi ảnh mức sạc `.png` → `.webp` | 4 ảnh trang `/charging` trả 404, để lại ô trống | `19-charging.css` |
| Trả `sectionKey` cho gallery | Ảnh chi tiết xe phải đoán chương theo tên file | `06-vehicle-detail.css` |
| API cấu hình 3 mẫu upsell | Đang chạy bộ mặc định trong code | `11-booking-upsell.css` |

---

## Quy ước khi sửa

- Sửa đúng file phụ trách khối đó, **đừng** nhét rule mới vào `01-foundation.css` cho tiện.
- File nền tảng chỉ chứa thứ dùng lại ở nhiều màn. Style của một khối thì ở lại file của khối.
- Giữ chú thích tiếng Việt đang có. Phần lớn giải thích **vì sao** một giá trị kỳ lạ lại cần
  thiết (ví dụ `transform` phải đặt cuối chuỗi, hay `overflow-x: clip` thay vì `hidden`).
  Xoá chú thích rồi "dọn" theo cảm tính là cách nhanh nhất làm vỡ giao diện.
