// Cloudflare rejects R2 object keys with path-like `..` segments.  Keep the
// original source filenames intact, but use these stable public object keys.
//
// Bảng này được dùng theo CẢ HAI CHIỀU — sửa thì nhớ cả hai:
//  - xuôi  (r2ObjectKey):     file trong kho  → key công khai, dùng khi dựng URL CDN.
//  - ngược (media/assets.js): key công khai   → file trong kho, dùng khi backend trả về
//    key công khai mà cần tìm file thật trong src/media/local/ để nhúng vào bundle.
// Thiếu chiều ngược thì ảnh VF 3 / VF 5 hiện "Ảnh đang được cập nhật" (đã xảy ra 16/08/2026).
export const r2KeyAliases = {
  'vehicle-media/VF3/1..webp': 'vehicle-media/VF3/1.webp',
  'vehicle-media/VF3/2..png': 'vehicle-media/VF3/exterior.png',
  'vehicle-media/VF3/3..jpg': 'vehicle-media/VF3/cockpit.jpg',
  'vehicle-media/VF3/4..png': 'vehicle-media/VF3/rear.png',
  'vehicle-media/VF5/1..webp': 'vehicle-media/VF5/1.webp',
  'vehicle-media/VF5/3..webp': 'vehicle-media/VF5/3.webp',
  'vehicle-media/VF5/4..webp': 'vehicle-media/VF5/4.webp',
  'vehicle-media/VF5/5..webp': 'vehicle-media/VF5/5.webp',
}

export const r2ObjectKey = (key) => r2KeyAliases[key] || key
