/**
 * data/vehicle-colors.js — BẢNG MÀU BỔ SUNG cho các mẫu xe backend chưa publish.
 *
 * Vì sao tồn tại: `GET /vehicles/{id}` trả `colors: []` cho 8/14 mẫu (kiểm 17/08/2026), nên
 * trang chủ in "Đang cập nhật" và trang chi tiết hiện khối rỗng, dù vinfast.vn đã công bố
 * đầy đủ. File này vá phần THIẾU đó bằng đúng dữ liệu chính hãng lấy từ bản crawl của anh Minh
 * (`~/Downloads/craw web html`) — KHÔNG bao giờ ghi đè màu backend đã có.
 *
 * TODO [BACKEND/CATALOGUE]: khi `colors` được publish cho các mẫu dưới đây thì XOÁ hẳn entry
 * tương ứng ở file này. Không để hai nguồn cùng mô tả một mẫu xe.
 *
 * ══ VÌ SAO SWATCH LÀ ẢNH, KHÔNG PHẢI MÃ HEX ══
 * Chính vinfast.vn cũng vẽ swatch bằng ảnh: `<button class="vf8-signature__swatch"><img
 * src="VF8PH-13.svg">` — file SVG đó nhúng một tấm ảnh chụp mảng sơn thật. Sơn xe có kim loại
 * và lớp phủ nên không quy về một mã hex phẳng được: em thử lấy mẫu pixel thì Vitality Orange
 * ra `#5f1210` (đỏ sẫm), sai hoàn toàn so với màu thật. Vì vậy mỗi màu ở đây mang `swatch` là
 * ẢNH chip chính hãng. Màu nào backend đã trả kèm hex thì vẫn vẽ bằng hex như cũ.
 *
 * ══ CẤU TRÚC MỘT MÀU ══
 *   name    — tên màu VinFast công bố (giữ nguyên tiếng Anh như trên vinfast.vn).
 *   swatch  — ảnh chip màu, hiện trong ô tròn ở trang chủ và ô vuông ở trang chi tiết.
 *   image   — ảnh chiếc xe mang đúng màu đó, dùng cho khối chọn màu ở trang chi tiết.
 *   group   — 'standard' | 'premium' để chia nhóm (chỉ VF 8 thế hệ mới có hai nhóm).
 *
 * ══ NGUỒN FILE ══
 * Toàn bộ nằm ở `src/media/local/colors/<mã xe>/`. Phần lớn chép thẳng từ thư mục crawl;
 * riêng ảnh xe của VF 8 thế hệ mới, 9 chip của Minio Green và 3 ảnh xe của Limo Green thì
 * bản lưu offline không có nên tải bổ sung từ đúng đường dẫn mà trang gốc trỏ tới.
 *
 * ══ MẪU CHƯA CÓ DỮ LIỆU, ĐỪNG TỰ BỊA ══
 * VF 6, VF MPV 7 và VinFast eBus: trang crawl KHÔNG hề nhắc tên màu nào và cũng không có
 * ảnh xe theo màu (VF 6 chỉ nói "hai màu nội thất", eBus không có chữ "màu"). Ba mẫu này
 * tiếp tục hiện "Đang cập nhật" cho tới khi có nguồn thật.
 */
import { colorAsset } from '../media/assets'

const color = (vehicleId, { name, swatch, hex, image, group }) => ({
  name,
  ...(swatch ? { swatch: colorAsset(vehicleId, swatch) } : {}),
  ...(hex ? { hex } : {}),
  image: colorAsset(vehicleId, image),
  ...(group ? { group } : {}),
})

/**
 * VF 8 thế hệ mới — 6 màu tiêu chuẩn + 6 màu nâng cao (phối thân/nóc).
 * Mã số 13–24 là mã biến thể của VinFast, giữ nguyên để đối chiếu được với trang gốc.
 */
const VF8_NEW = [
  { code: 13, name: 'Solar Ruby', group: 'standard' },
  { code: 15, name: 'Infinity Blanc', group: 'standard' },
  { code: 21, name: 'Jet Black', group: 'standard' },
  { code: 23, name: 'Starburst Blue', group: 'standard' },
  { code: 17, name: 'Mysterioso Purple', group: 'standard' },
  { code: 19, name: 'Vitality Orange', group: 'standard' },
  { code: 14, name: 'Solar Ruby · nóc Jet Black', group: 'premium' },
  { code: 16, name: 'Vitality Orange · nóc Infinity Blanc', group: 'premium' },
  { code: 18, name: 'Mysterioso Purple · nóc Stealth Gray', group: 'premium' },
  { code: 20, name: 'Vitality Orange · nóc Jet Black', group: 'premium' },
  { code: 22, name: 'Jet Black · nóc Stealth Gray', group: 'premium' },
  { code: 24, name: 'Starburst Blue · nóc Infinity Blanc', group: 'premium' },
]

/** Minio Green — 14 màu, tên lấy từ mảng `colorData` trong JS của trang gốc. */
const MINIO = [
  ['black', 'Jet Black'],
  ['gray', 'Desat Silver'],
  ['white-2', 'Infinity Blanc'],
  ['red', 'Solar Ruby'],
  ['purple', 'Rose Metallic'],
  ['green-2', 'Tropical Jade'],
  ['black-gray', 'Desat Silver · nóc Jet Black'],
  ['cyan-purple', 'Rose Metallic · nóc Aqua Blue'],
  ['gray-green', 'Tropical Jade · nóc Desat Silver'],
  ['gray-purple', 'Rose Metallic · nóc Desat Silver'],
  ['gray-red', 'Solar Ruby · nóc Infinity Blanc'],
  ['gray-yellow', 'Summer Yellow · nóc Infinity Blanc'],
  ['yellow-black', 'Jet Black · nóc Summer Yellow'],
  ['yellow-green', 'Tropical Jade · nóc Summer Yellow'],
]

/** Limo Green — 4 màu, tên lấy từ `.limo-color-item` trong HTML gốc. */
const LIMO = [
  ['black', 'Jet Black'],
  ['silver', 'Desat Silver'],
  ['red', 'Solar Ruby'],
  ['white', 'Infinity Blanc'],
]

/**
 * Nerio Green — 4 màu. ĐÂY LÀ MỤC DUY NHẤT TRONG FILE KHÔNG CÓ TÊN MÀU CHÍNH THỨC:
 * trang crawl chỉ có 12 ảnh studio (4 màu × 3 góc) mà không hề đặt tên màu nào, cũng không
 * có chip màu. Nên em gọi tên tiếng Việt theo đúng cách backend đang gọi màu Herio Green
 * ("Trắng · Đen · Đỏ"), và lấy mã hex bằng cách đo pixel trên mảng thân xe ở chính ảnh đó —
 * KHÔNG bịa mã. Có tên chính thức từ VinFast thì thay lại.
 */
const NERIO = [
  ['black', 'Đen', '#363636'],
  ['silver', 'Bạc', '#b3b3b3'],
  ['red', 'Đỏ', '#c42222'],
  ['yellow', 'Vàng', '#dbbe3f'],
]

/**
 * EC Van — 4 màu. Trang gốc gọi tên tiếng Việt ("Xanh ngọc, vàng, trắng, đỏ") chứ không dùng
 * bộ tên tiếng Anh như xe cá nhân, nên giữ đúng cách gọi đó.
 */
const EC_VAN = [
  ['jade', 'Xanh ngọc'],
  ['yellow', 'Vàng'],
  ['white', 'Trắng'],
  ['red', 'Đỏ'],
]

const SUPPLEMENTAL_COLORS = {
  'vf8-the-he-moi': VF8_NEW.map(({ code, name, group }) => color('vf8-the-he-moi', {
    name,
    group,
    swatch: `swatch-${code}.svg`,
    image: `car-${code}.webp`,
  })),
  'minio-green': MINIO.map(([key, name]) => color('minio-green', {
    name,
    swatch: `swatch-${key}.webp`,
    image: `car-${key}.webp`,
  })),
  'limo-green': LIMO.map(([key, name]) => color('limo-green', {
    name,
    swatch: `swatch-${key}.webp`,
    image: `car-${key}.webp`,
  })),
  'nerio-green': NERIO.map(([key, name, hex]) => color('nerio-green', {
    name,
    hex,
    image: `car-${key}.webp`,
  })),
  'ec-van': EC_VAN.map(([key, name]) => color('ec-van', {
    name,
    swatch: `swatch-${key}.png`,
    image: `car-${key}.webp`,
  })),
}

/**
 * Màu bổ sung cho một mẫu xe. Trả mảng rỗng nếu mẫu đó không nằm trong bảng trên, hoặc nếu
 * file ảnh vì lý do nào đó không có trong bundle — thà thiếu swatch còn hơn hiện ô vỡ.
 */
export function supplementalColors(vehicleId) {
  return (SUPPLEMENTAL_COLORS[vehicleId] || [])
    .filter((entry) => entry.image && (entry.swatch || entry.hex))
}

/**
 * Ghép màu backend với màu bổ sung. Backend LUÔN thắng: chỉ khi backend không trả màu nào
 * thì mới lấy bảng ở đây ra dùng, tránh cảnh hai nguồn mô tả lệch nhau về cùng một mẫu xe.
 */
export function withSupplementalColors(vehicleId, backendColors) {
  if (Array.isArray(backendColors) && backendColors.length) return backendColors
  return supplementalColors(vehicleId)
}
