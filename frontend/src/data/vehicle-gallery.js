/**
 * data/vehicle-gallery.js — ẢNH SẢN PHẨM BỔ SUNG cho trang chi tiết xe.
 *
 * Vì sao tồn tại: backend chỉ trả 2–3 `chapters` và một ít `gallery` cho mỗi mẫu xe, nên
 * trang chi tiết rất nghèo hình (có mẫu còn trống hẳn một mục). File này gom thêm ảnh chính
 * hãng tải từ vinfast.vn để trang có nhiều góc nhìn hơn.
 *
 * KHÔNG đụng tới giá, mô tả hay thông số — những thứ đó vẫn hoàn toàn do backend quyết định.
 * File này CHỈ thêm ảnh và nhãn mô tả góc chụp.
 *
 * ══ QUY TẮC NỀN — quan trọng nhất khi thêm ảnh mới ══
 * Ảnh phải hợp với nền nơi nó đứng, nếu không trang sẽ rất lộn xộn. Ba kiểu:
 *
 *   'cutout' — ảnh tách nền (nền trong suốt). Đặt THẲNG lên nền giấy sáng của web, KHÔNG
 *              đóng khung. Đóng khung ảnh tách nền sẽ lộ ra một hộp trắng vô nghĩa.
 *   'photo'  — ảnh chụp thật, nền sáng/trung tính. Đóng khung `double-bezel` sáng.
 *   'dark'   — ảnh chụp thật, tông tối (nội thất, ảnh đêm). Đóng khung `double-bezel--dark`
 *              để viền hoà vào ảnh thay vì cắt ngang nó.
 *
 * ══ ẢNH BỊ LOẠI, ĐỪNG THÊM LẠI ══
 * - Ảnh có SẴN CHỮ marketing nung trong file (vf3bannermobile, vf7-lead-banner, VF6-banner):
 *   đá nhau với typography của web, và không dịch/sửa được.
 * - Ảnh SAI MẪU XE: thư mục crawl của VF7 MPV và VF8 thế hệ mới có lẫn ảnh xe buýt điện và
 *   xe máy điện (vehicle-ebus, vehicle-xemay).
 * - Bản đồ, sơ đồ, logo, icon.
 *
 * ══ THÊM ẢNH MỚI ══
 * 1. Bỏ file vào `src/media/local/gallery/<mã xe>/<mục>-<tên>.<ext>`
 *    `<mục>` phải là exterior | interior | technology — đây là thứ quyết định ảnh vào mục nào.
 * 2. Thêm nhãn vào `GALLERY_LABELS` bên dưới nếu tên chưa có.
 * 3. Khai báo kiểu nền trong `GALLERY_TONES` nếu khác mặc định ('photo').
 *
 * Mã xe phải khớp `id` backend trả về (vf3, vf5, vf6, vf7, vf-mpv-7, vf8, vf8-the-he-moi, vf9,
 * herio-green, minio-green, nerio-green, limo-green, ec-van, ebus).
 *
 * Dải xe DỊCH VỤ được bổ sung 17/08/2026 từ 6 trang crawl mới (Nerio · Limo · Minio · Herio ·
 * EC Van · eBus). Hai việc phải làm thêm so với xe cá nhân:
 * - Ảnh studio của Nerio và Limo có tới 60% diện tích là nền trắng → đã cắt sát chiếc xe
 *   trước khi đưa vào, để nguyên thì ô ảnh trong gallery gần như trống.
 * - Ảnh của EC Van là 3840×2160 → đã thu về 1920 px, giữ nguyên độ nét nhưng nhẹ hơn 6 lần.
 */
import { vehicleGalleryAssets } from '../media/assets'

/** Nhãn theo phần <tên> của file. Chỉ mô tả GÓC CHỤP, không phải lời quảng cáo. */
const GALLERY_LABELS = {
  'rear-quarter': 'Góc chéo sau',
  'front-quarter': 'Góc chéo trước',
  'top-view': 'Nhìn từ trên xuống',
  hero: 'Toàn cảnh',
  studio: 'Góc nhìn sản phẩm',
  'rear-motion': 'Đuôi xe trong chuyển động',
  journey: 'Trên hành trình',
  dashboard: 'Bảng táp-lô',
  airbags: 'Hệ thống túi khí',
  city: 'Trong phố',
  coast: 'Cung đường ven biển',
  residence: 'Trước hiên nhà',
  red: 'Ngoại thất màu đỏ',
  side: 'Nhìn ngang',
  cabin: 'Khoang nội thất',
  console: 'Bệ trung tâm',
  'cabin-side': 'Khoang lái nhìn từ cửa',
  mountain: 'Cung đường đèo',
  people: 'Cùng người thân',
  'front-seats': 'Hàng ghế trước',
  'rear-seats': 'Hàng ghế sau',
  boot: 'Khoang hành lý',
  cockpit: 'Khoang lái',
  charging: 'Nạp điện',
  'charge-port': 'Cổng sạc',
  driving: 'Vận hành',
  rain: 'Dưới trời mưa',
  station: 'Tại điểm dừng',
  aisle: 'Lối đi giữa khoang',
  'doors-open': 'Mở cửa khoang hàng',
  front: 'Đầu xe',
}

/**
 * Kiểu nền của từng ảnh, tra theo "<mã xe>/<tên file không đuôi>".
 * Đã xem TỪNG ảnh một để xếp, không suy từ tên file.
 */
const GALLERY_TONES = {
  'vf3/exterior-side-profile': 'cutout',
  'vf3/exterior-rear-quarter': 'cutout',
  'vf3/interior-cabin': 'dark',
  'vf5/exterior-grey': 'cutout',
  'vf5/exterior-yellow': 'cutout',
  'vf5/exterior-red': 'cutout',
  'vf5/interior-steering': 'dark',
  'vf5/interior-front-seats': 'dark',
  'vf5/interior-boot': 'dark',
  'vf6/interior-dashboard': 'dark',
  'vf6/interior-steering': 'dark',
  'vf6/interior-centre-screen': 'dark',
  'vf7/exterior-black': 'cutout',
  'vf7/exterior-red': 'cutout',
  'vf7/exterior-hero': 'cutout',
  'vf7/exterior-rear-motion': 'dark',
  'vf7/exterior-front-motion': 'dark',
  'vf7/interior-cabin': 'dark',
  'vf7/interior-front-seats': 'dark',
  'vf-mpv-7/exterior-front-quarter': 'cutout',
  'vf-mpv-7/exterior-side': 'cutout',
  'vf-mpv-7/exterior-rear-quarter': 'cutout',
  'vf8/exterior-black': 'cutout',
  'vf8/exterior-red': 'cutout',
  'vf8/exterior-green': 'cutout',
  'vf8/interior-cabin': 'dark',
  'vf8/interior-cabin-side': 'dark',
  'vf8/interior-airbags': 'dark',
  'vf8/technology-cockpit': 'dark',
  'vf8/technology-driver-assist': 'dark',
  'vf8-the-he-moi/exterior-red': 'cutout',
  'vf8-the-he-moi/exterior-rear-quarter': 'cutout',
  'vf8-the-he-moi/interior-console': 'dark',
  'vf8-the-he-moi/interior-cabin': 'dark',
  'vf8-the-he-moi/exterior-mountain': 'dark',
  'vf9/exterior-top-view': 'cutout',
  'vf9/exterior-residence': 'dark',
  'vf9/interior-cabin': 'dark',

  // ── Dải xe dịch vụ (thêm 17/08/2026) ──────────────────────────────────────
  // Ảnh studio nền trong suốt của Nerio và Limo: đặt thẳng lên nền giấy, không đóng khung.
  'nerio-green/exterior-front-quarter': 'cutout',
  'nerio-green/exterior-side': 'cutout',
  'nerio-green/exterior-rear-quarter': 'cutout',
  'limo-green/exterior-front-quarter': 'cutout',
  'limo-green/exterior-side': 'cutout',
  'ec-van/exterior-front-quarter': 'cutout',
  'ec-van/exterior-front': 'cutout',
  'ec-van/exterior-side': 'cutout',
  'ec-van/exterior-doors-open': 'cutout',
  'minio-green/interior-top-view': 'cutout',
  // Ảnh chụp tông tối: nền đen tuyền hoặc trời mưa đêm, phải dùng khung tối kẻo viền cắt ngang ảnh.
  'herio-green/exterior-rain': 'dark',
  'herio-green/exterior-front-quarter': 'dark',
  'herio-green/interior-top-view': 'dark',
  'herio-green/interior-rear-seats': 'dark',
  'herio-green/interior-cockpit': 'dark',
  'herio-green/interior-front-seats': 'dark',
  'herio-green/interior-dashboard': 'dark',
  'limo-green/interior-front-seats': 'dark',
  'minio-green/interior-dashboard': 'dark',
  'minio-green/interior-rear-seats': 'dark',
}

/**
 * Tỉ lệ khung hình THẬT của từng ảnh (rộng/cao), đo trực tiếp từ file.
 *
 * Vì sao phải có: bộ ảnh này trải từ 0,625 (ảnh dọc của VF 7 MPV) tới 2,628 (ảnh siêu ngang
 * của VF 7) — chênh hơn 4 lần. Bản đầu em đặt khung cứng 4:3 rồi ép ảnh vào, kết quả là ảnh
 * dọc teo lại giữa hai mảng trống còn ảnh siêu ngang bị cắt cụt đầu đuôi.
 * Khung bám theo tỉ lệ ảnh thì `contain` không thừa chỗ, `cover` không cắt gì cả.
 *
 * Giá trị đã kẹp trong [0,78 – 2,6] để không ô nào cao lêu nghêu hay dẹt như sợi chỉ.
 * THÊM ẢNH MỚI thì chạy lại script đo, đừng tự điền bằng mắt.
 */
const GALLERY_RATIOS = {
  'vf-mpv-7/exterior-front-quarter': 0.78,
  'vf-mpv-7/exterior-rear-quarter': 0.78,
  'vf-mpv-7/exterior-side': 0.78,
  'vf-mpv-7/interior-cabin': 0.78,
  'vf3/exterior-front-quarter': 2.558,
  'vf3/exterior-rear-quarter': 2.138,
  'vf3/exterior-side-profile': 2.354,
  'vf3/exterior-studio': 1.776,
  'vf3/interior-cabin': 1.885,
  'vf5/exterior-grey': 1.78,
  'vf5/exterior-red': 1.78,
  'vf5/exterior-yellow': 1.78,
  'vf5/interior-boot': 1.778,
  'vf5/interior-front-seats': 1.778,
  'vf5/interior-steering': 1.778,
  'vf5/technology-driving': 1.301,
  'vf6/exterior-city': 0.936,
  'vf6/exterior-coast': 1.875,
  'vf6/exterior-people': 1.875,
  'vf6/exterior-journey': 0.935,
  'vf6/interior-centre-screen': 1.546,
  'vf6/interior-dashboard': 1.913,
  'vf6/interior-steering': 1.545,
  'vf7/exterior-black': 1.778,
  'vf7/exterior-front-motion': 0.867,
  'vf7/exterior-hero': 2.6,
  'vf7/exterior-rear-motion': 1.778,
  'vf7/exterior-red': 1.778,
  'vf7/interior-cabin': 1.775,
  'vf7/interior-front-seats': 1.076,
  'vf7/technology-charging': 1.778,
  'vf8-the-he-moi/exterior-city': 0.944,
  'vf8-the-he-moi/exterior-coast': 0.935,
  'vf8-the-he-moi/exterior-city': 1.08,
  'vf8-the-he-moi/exterior-rear-quarter': 2.315,
  'vf8-the-he-moi/exterior-red': 1.791,
  'vf8-the-he-moi/interior-cabin': 0.944,
  'vf8-the-he-moi/interior-console': 2.066,
  'vf8-the-he-moi/exterior-mountain': 1.533,
  'vf8/exterior-black': 2.402,
  'vf8/exterior-green': 2.402,
  'vf8/exterior-red': 2.402,
  'vf8/interior-airbags': 2.402,
  'vf8/interior-cabin': 2.402,
  'vf8/interior-cabin-side': 2.402,
  'vf8/technology-cockpit': 2.263,
  'vf8/technology-driver-assist': 2.263,
  'vf9/exterior-residence': 1.547,
  'vf9/exterior-top-view': 1.987,
  'vf9/interior-cabin': 2.283,
  'vf9/interior-console': 0.938,
  'vf9/interior-rear-seats': 0.938,
  'vf9/technology-charge-port': 1.442,

  // ── Dải xe dịch vụ ────────────────────────────────────────────────────────
  'ebus/exterior-city': 0.78,
  'ebus/exterior-station': 0.78,
  'ebus/interior-aisle': 0.78,
  'ebus/interior-rear-seats': 0.78,
  'ec-van/exterior-doors-open': 2.18,
  'ec-van/exterior-front': 1.742,
  'ec-van/exterior-front-quarter': 1.707,
  'ec-van/exterior-side': 1.879,
  'herio-green/exterior-front-quarter': 1.429,
  'herio-green/exterior-rain': 1.0,
  'herio-green/interior-cockpit': 1.351,
  'herio-green/interior-dashboard': 1.334,
  'herio-green/interior-front-seats': 1.334,
  'herio-green/interior-rear-seats': 1.334,
  'herio-green/interior-top-view': 1.502,
  'limo-green/exterior-front-quarter': 1.645,
  'limo-green/exterior-side': 2.48,
  'limo-green/interior-front-seats': 1.0,
  'minio-green/exterior-city': 1.921,
  'minio-green/exterior-rear-quarter': 0.975,
  'minio-green/interior-cockpit': 0.975,
  'minio-green/interior-dashboard': 1.0,
  'minio-green/interior-rear-seats': 1.0,
  'minio-green/interior-top-view': 0.891,
  'nerio-green/exterior-front-quarter': 2.034,
  'nerio-green/exterior-rear-quarter': 2.011,
  'nerio-green/exterior-side': 2.588,
}

const SECTIONS = new Set(['exterior', 'interior', 'technology'])

/**
 * Ảnh bổ sung của một mẫu xe, đã gom theo mục.
 * Trả về { exterior: [...], interior: [...], technology: [...] }.
 * Mẫu xe không có thư mục ảnh (dải xe dịch vụ) thì trả về ba mảng rỗng — trang giữ nguyên
 * như cũ, không có gì đổi.
 */
export function vehicleGallery(vehicleId) {
  const grouped = { exterior: [], interior: [], technology: [] }
  if (!vehicleId) return grouped

  vehicleGalleryAssets(vehicleId).forEach(({ file, src }) => {
    const base = file.replace(/\.[^.]+$/, '')
    const [section, ...rest] = base.split('-')
    if (!SECTIONS.has(section) || !rest.length) return
    const key = rest.join('-')
    const ratio = GALLERY_RATIOS[`${vehicleId}/${base}`] || 1.6
    grouped[section].push({
      src,
      key: `${section}-${key}`,
      label: GALLERY_LABELS[key] || 'Góc nhìn sản phẩm',
      tone: GALLERY_TONES[`${vehicleId}/${base}`] || 'photo',
      ratio,
      // Ảnh càng ngang thì đặt trong ô hẹp càng thành sợi chỉ → cho chiếm 2 cột.
      wide: ratio >= 1.9,
    })
  })

  return grouped
}
