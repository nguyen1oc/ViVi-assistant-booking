# Thư mục ghi đè ảnh theo mẫu xe

Muốn đổi ảnh của một mẫu xe, **bỏ file vào đây** — không cần đi tìm ảnh cũ nằm ở thư mục nào.

## Cách dùng

Mỗi mẫu xe có một thư mục mang đúng **mã xe của backend**. Bỏ file vào với đúng một trong
bốn tên dưới đây (phần đuôi `.png` / `.webp` / `.jpg` đều được, code tự nhận):

| Tên file | Thay cho |
|---|---|
| `thumbnail.*` | Ảnh thẻ xe ở trang chủ và trong luồng đặt lịch |
| `studio.*` | Ảnh studio (thường dùng chung với thumbnail) |
| `hero.*` | Ảnh lớn đầu trang chi tiết xe |
| `video.mp4` | Video giới thiệu |

Ví dụ — đổi ảnh VF 9:

```text
src/media/local/by-model/vf9/studio.png     ← bỏ file mới vào đây là xong
```

Không cần sửa dòng code nào. Xoá file đi thì tự động quay lại ảnh cũ trong kho.

## 14 mã xe

```text
vf3   vf5   vf6   vf7   vf-mpv-7   vf8   vf8-the-he-moi   vf9
herio-green   minio-green   nerio-green   limo-green   ec-van   ebus
```

Gõ sai mã là ảnh không được nhận. Copy từ danh sách trên cho chắc.

## Sau khi bỏ ảnh vào

- **Ảnh marketing** (trang chủ, trang chi tiết): Vite tự nạp lại, F5 là thấy ngay.
- **Ảnh thẻ xe** (`thumbnail` / `studio`): những ảnh này do backend phục vụ, nên phải chạy lại
  `bash frontend/dev-local.sh` một lần để đẩy ảnh mới sang backend. Script tự làm, không cần thao tác thêm.

## Vì sao có thư mục này

Kho ảnh gốc trong `../vehicle-media/` có tên thư mục không khớp mã xe
(`VF8 All the new` ↔ `vf8-the-he-moi`, `Dịch vụ_ EC Van` thừa một dấu cách), và ảnh chính của
5 mẫu xe lại nằm lẫn trong `../common/`. Di chuyển hết sang tên mới sẽ đụng nhánh của backend
và làm hỏng `publish_site_media.py` của họ, nên thay vì dọn, ta thêm một lớp ghi đè ở đây.

Muốn tra ảnh cũ đang nằm đâu: mở `frontend/media-index.html`, hoặc đọc
`src/media/vehicle-media-map.js`.
