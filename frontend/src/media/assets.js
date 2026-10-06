/**
 * media/assets.js — Cầu nối tới kho ảnh/video/brochure nằm trong src/media/local/ (~180 MB).
 *
 * Vite quét sẵn toàn bộ thư mục local/ lúc build (import.meta.glob) rồi đóng gói vào dist,
 * nên file này KHÔNG tải gì từ mạng. Đây là kho ảnh của các trang marketing.
 *
 * Phân biệt 2 nguồn ảnh trong dự án — hay nhầm:
 * - Ảnh CATALOGUE XE  → backend trả URL /media/... (phải publish sang backend/data/media).
 * - Ảnh MARKETING     → file này, nhúng thẳng vào bundle, luôn hiển thị được.
 *
 * 3 thư mục nguồn: local/vehicle-media/ (ảnh+video theo mẫu xe) · local/common/ (logo, ViVi,
 * ảnh dùng chung) · local/brochures/ (PDF).
 *
 * Hàm chính:
 * - vehicleImage(path) · vehicleVideo(path): lấy 1 file theo đường dẫn tương đối.
 * - vehicleAssetByName(folder, ten): tìm file trong 1 thư mục con, ví dụ "Trạm sạc".
 * - vehicleAssetsIn(...folders): lấy TẤT CẢ ảnh trong nhiều thư mục (dùng cho gallery).
 * - brochureByKeyword(tu): tìm PDF theo từ khoá trong tên file.
 * - commonMedia: object liệt kê sẵn các ảnh dùng chung (logo, viviAvatar, vf9Studio…).
 *
 * Thứ tự ưu tiên khi lấy ảnh (mới nhất thắng):
 *   1. local/by-model/<mã xe>/<slot>.*  — lớp ghi đè, xem local/by-model/README.md
 *   2. File trong local/vehicle-media/ hoặc local/common/ hoặc local/showcase/
 *   3. CDN, nếu có đặt VITE_MEDIA_BASE_URL
 *
 * Tên file tiếng Việt được chuẩn hoá Unicode NFC — đừng bỏ bước này, macOS lưu khác Windows.
 * Bảng "mẫu xe nào dùng ảnh nào" nằm ở ./vehicle-media-map.js.
 */
import { vehicleMediaMap } from './vehicle-media-map'
import { r2KeyAliases, r2ObjectKey } from './r2-key-aliases'

const vehicleImageModules = import.meta.glob('./local/vehicle-media/**/*.{png,jpg,jpeg,webp,svg}', {
  eager: true,
  query: '?url',
  import: 'default',
})

const vehicleVideoModules = import.meta.glob('./local/vehicle-media/**/*.{mp4,mov}', {
  eager: true,
  query: '?url',
  import: 'default',
})

/*
 * KHÔNG glob brochure nữa (gỡ 17/08/2026).
 *
 * `eager: true` khiến Vite nhét TOÀN BỘ 11 file PDF vào dist — 49,5 MB — trong khi frontend
 * chỉ tra brochure cho đúng hai từ khoá ('bảo hành', 'pin ô tô'), và hai file đó trong kho chỉ
 * nặng 1 byte (bản giữ chỗ, tải về là hỏng). Brochure của từng mẫu xe do BACKEND phục vụ qua
 * `/media/brochures/<mã xe>.pdf`, `resolveVehicleMedia` không hề đụng tới kho local này.
 * Nay brochureByKeyword() chỉ còn trả URL CDN khi có VITE_MEDIA_BASE_URL.
 */
const commonImageModules = import.meta.glob('./local/common/*.{png,jpg,jpeg,webp,svg}', {
  eager: true,
  query: '?url',
  import: 'default',
})

const overrideModules = import.meta.glob('./local/by-model/*/*.{png,jpg,jpeg,webp,svg,mp4,mov}', {
  eager: true,
  query: '?url',
  import: 'default',
})

const showcaseModules = import.meta.glob('./local/showcase/*/*.{png,jpg,jpeg,webp}', {
  eager: true,
  query: '?url',
  import: 'default',
})

// Ảnh sản phẩm bổ sung, xếp theo MÃ XE của backend: ./local/gallery/<mã xe>/<mục>-<tên>.<ext>
// Đây là ảnh chính hãng lấy từ trang vinfast.vn, dùng để làm dày phần hình của trang chi tiết.
// KHÁC với vehicle-media/: thư mục kia là kho gốc do backend publish, thư mục này chỉ frontend đọc.
// Bảng chú thích và phân loại nền nằm ở data/vehicle-gallery.js.
const galleryModules = import.meta.glob('./local/gallery/*/*.{png,jpg,jpeg,webp}', {
  eager: true,
  query: '?url',
  import: 'default',
})

// Ảnh xe cho khối mời chọn xe ở khung chat: ./local/upsell/<mã xe>.webp
// Đây là bản ĐÃ CHUẨN HOÁ từ ảnh studio gốc — xe cùng bề ngang và cùng đường bánh xe trên một
// khung 320×180. Ảnh studio gốc mỗi mẫu một tỉ lệ (1,78 · 2,40 · 2,62…) nên khi cùng
// `object-fit: contain` trong ô nhỏ, ba chiếc xe nằm ở ba độ cao khác nhau (đo được lệch tới
// 4,6px trong ô cao 48px) — nhìn như trôi lửng, không thành một hàng.
// Chiều cao giữa các xe VẪN chênh nhau theo đúng tỉ lệ thật; chỉ đường bánh xe là chung.
const upsellModules = import.meta.glob('./local/upsell/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
})

// Swatch màu + ảnh xe theo từng màu: ./local/colors/<mã xe>/{swatch|car}-<khoá>.<ext>
// Chỉ dùng cho các mẫu backend CHƯA publish `colors` (xem data/vehicle-colors.js).
const colorModules = import.meta.glob('./local/colors/*/*.{png,jpg,jpeg,webp,svg}', {
  eager: true,
  query: '?url',
  import: 'default',
})

const mediaBaseUrl = (import.meta.env.VITE_MEDIA_BASE_URL || '').replace(/\/+$/, '')
const normalizePath = (path) => path.normalize('NFC').replace(/^\/+/, '')
const encodePath = (path) => normalizePath(path).split('/').map(encodeURIComponent).join('/')
const cdnUrl = (scope, relativePath) => {
  if (!mediaBaseUrl) return ''
  const objectKey = r2ObjectKey(`${scope}/${normalizePath(relativePath)}`)
  return `${mediaBaseUrl}/${encodePath(objectKey)}`
}

const normalizeModules = (modules) =>
  Object.fromEntries(Object.entries(modules).map(([key, url]) => [key.normalize('NFC'), url]))

const vehicleImages = normalizeModules(vehicleImageModules)
const vehicleVideos = normalizeModules(vehicleVideoModules)
const commonImages = normalizeModules(commonImageModules)
const showcaseImages = normalizeModules(showcaseModules)

/*
 * Chỉ mục phụ theo đường dẫn ĐÃ BỎ ĐUÔI.
 *
 * Vì sao cần: ảnh trong kho đã được nén lại sang .webp để giảm dung lượng, nhưng tên file cũ
 * (.png/.jpg) còn nằm rải rác ở backend (`/media/vehicle-media/VF3/đỏ.png`), ở vehicle-media-map.js
 * và ở r2-key-aliases.js. Sửa hết những chỗ đó vừa nhiều vừa dễ sót — sót một chỗ là người dùng
 * thấy "Ảnh đang được cập nhật". Thay vào đó, khi tra thẳng trượt thì thử lại theo tên không đuôi.
 */
const stripExtension = (path) => path.replace(/\.[^./]+$/, '')

const indexWithoutExtension = (modules) => Object.entries(modules).reduce((index, [key, url]) => {
  const bare = stripExtension(key)
  // Trùng tên khác đuôi thì giữ bản ĐẦU theo thứ tự chữ cái, để kết quả luôn ổn định.
  if (!(bare in index)) index[bare] = url
  return index
}, {})

const localAsset = (modules, root, relativePath) => {
  const key = `${root}/${normalizePath(relativePath)}`.normalize('NFC')
  if (modules[key]) return modules[key]
  const bare = stripExtension(key)
  return extensionlessIndex.get(modules)?.[bare] || ''
}

/** Dựng chỉ mục không-đuôi một lần cho mỗi bộ module, tra sau đó chỉ là đọc object. */
const extensionlessIndex = new WeakMap()

;[vehicleImages, commonImages, showcaseImages].forEach((modules) => {
  extensionlessIndex.set(modules, indexWithoutExtension(modules))
})

const overrides = normalizeModules(overrideModules)
const galleryImages = normalizeModules(galleryModules)
const colorImages = normalizeModules(colorModules)
const upsellImages = normalizeModules(upsellModules)

/** Ảnh xe đã chuẩn hoá cho khối mời chọn xe. Trả '' nếu mẫu đó chưa có bản chuẩn hoá. */
export const upsellThumb = (vehicleId) =>
  upsellImages[`./local/upsell/${normalizePath(vehicleId)}.webp`.normalize('NFC')] || ''

/** URL của một file trong kho màu, vd colorAsset('minio-green', 'swatch-red.webp'). */
export const colorAsset = (vehicleId, file) =>
  colorImages[`./local/colors/${normalizePath(vehicleId)}/${normalizePath(file)}`.normalize('NFC')] || ''

/** Toàn bộ ảnh bổ sung của một mẫu xe: [{ file, src }], đã sắp theo tên file. */
export const vehicleGalleryAssets = (vehicleId) => {
  const prefix = `./local/gallery/${normalizePath(vehicleId)}/`.normalize('NFC')
  return Object.entries(galleryImages)
    .filter(([key]) => key.startsWith(prefix))
    .map(([key, src]) => ({ file: key.slice(prefix.length), src }))
    .sort((left, right) => left.file.localeCompare(right.file))
}

const slotByLegacyPath = Object.entries(vehicleMediaMap).reduce((index, [id, entry]) => {
  if (entry.thumbnail) {
    index[entry.thumbnail.normalize('NFC')] = { id, slots: ['thumbnail', 'studio'] }
  }
  if (entry.video) index[entry.video.normalize('NFC')] = { id, slots: ['video'] }
  return index
}, {})

const overrideUrl = (vehicleId, slot) => {
  const prefix = `./local/by-model/${vehicleId}/${slot}.`.normalize('NFC')
  const match = Object.keys(overrides).filter((key) => key.startsWith(prefix)).sort()[0]
  return match ? overrides[match] : ''
}

const overrideForLegacyPath = (relativePath, scope = '') => {
  const entry = slotByLegacyPath[`${scope}${normalizePath(relativePath)}`.normalize('NFC')]
  if (!entry) return ''
  for (const slot of entry.slots) {
    const url = overrideUrl(entry.id, slot)
    if (url) return url
  }
  return ''
}

/*
 * Bảng đảo chiều của r2KeyAliases.
 *
 * r2KeyAliases đi theo chiều "file thật trong kho → key công khai trên R2", vì Cloudflare
 * không nhận key có đoạn `..` (kho có mấy file lỡ thừa một dấu chấm: `VF3/2..png`, `VF5/4..webp`).
 * Backend lại trả về đúng KEY CÔNG KHAI, ví dụ /media/vehicle-media/VF3/exterior.png — mà file
 * đó KHÔNG tồn tại trong local/, nên tra thẳng là trượt và người dùng thấy "Ảnh đang được cập nhật".
 *
 * Triệu chứng đã gặp 16/08/2026: đúng 7 ảnh vỡ trên toàn site, tất cả ở VF 3 (ngoại thất,
 * khoang lái, đuôi xe) và VF 5 (1/3/4/5.webp). Đã đối chiếu bằng mắt từng ảnh: ánh xạ trong
 * r2KeyAliases khớp đúng nội dung ảnh, không phải phỏng đoán theo tên file.
 *
 * Không thêm dữ liệu mới ở đây — chỉ đọc lại bảng đã có theo chiều ngược.
 */
const localPathByPublicKey = Object.entries(r2KeyAliases).reduce((index, [sourceKey, publicKey]) => {
  const strip = (key) => key.replace(/^vehicle-media\//, '').normalize('NFC')
  index[strip(publicKey)] = strip(sourceKey)
  return index
}, {})

export const vehicleImage = (relativePath) => {
  const direct = overrideForLegacyPath(relativePath)
    || localAsset(vehicleImages, './local/vehicle-media', relativePath)
  if (direct) return direct

  // Chỉ dùng bảng đảo chiều khi tra thẳng đã trượt, để không đổi hành vi của mọi ảnh khác.
  const sourcePath = localPathByPublicKey[normalizePath(relativePath)]
  if (sourcePath) {
    const aliased = overrideForLegacyPath(sourcePath)
      || localAsset(vehicleImages, './local/vehicle-media', sourcePath)
    if (aliased) return aliased
  }

  // Lên CDN vẫn dùng đường dẫn gốc: cdnUrl() tự chạy r2ObjectKey() để ra key công khai.
  return cdnUrl('vehicle-media', relativePath)
}

export const vehicleVideo = (relativePath) =>
  overrideForLegacyPath(relativePath) ||
  localAsset(vehicleVideos, './local/vehicle-media', relativePath) ||
  cdnUrl('vehicle-media', relativePath)

export const commonImage = (fileName) =>
  overrideForLegacyPath(fileName, 'common/') ||
  localAsset(commonImages, './local/common', fileName) ||
  cdnUrl('common', fileName)

export const modelImage = (vehicleId) => {
  const relativePath = vehicleMediaMap[vehicleId]?.thumbnail || ''

  if (!relativePath) return ''
  if (relativePath.startsWith('common/')) {
    return commonImage(relativePath.slice('common/'.length))
  }

  return vehicleImage(relativePath)
}

export const modelOverride = (vehicleId, slot) => overrideUrl(vehicleId, slot)

export const showcaseImage = (relativePath) => {
  const [modelId, fileName] = normalizePath(relativePath).split('/')
  const slot = fileName?.replace(/\.[^.]+$/, '')
  return (
    (modelId && slot ? overrideUrl(modelId, slot) : '') ||
    localAsset(showcaseImages, './local/showcase', relativePath) ||
    cdnUrl('showcase', relativePath)
  )
}

/* Hai brochure chính sách không thuộc mẫu xe nào, chỉ tồn tại trên CDN. */
const brochureCdnNames = {
  'bảo hành': 'Chính sách bảo hành Ô tô VinFast - VinFast.pdf',
  'pin ô tô': 'Dịch vụ pin ô tô điện VinFast - VinFast.pdf',
}

export const brochureByKeyword = (keyword) => {
  // Kho local đã gỡ (xem ghi chú ở phần khai báo glob). Không có CDN thì trả '' và giao diện
  // tự ẩn link — thà không có link còn hơn link tải về một file 1 byte như trước.
  const target = normalizePath(keyword).toLowerCase()
  return brochureCdnNames[target] ? cdnUrl('brochures', brochureCdnNames[target]) : ''
}

export const vehicleAssetByName = (folder, fileName) => {
  const prefix = `./local/vehicle-media/${normalizePath(folder)}/`
  const local = Object.entries(vehicleImages).find(([path]) =>
    path.startsWith(prefix.normalize('NFC')) && path.endsWith(fileName),
  )?.[1] || ''
  return local || cdnUrl('vehicle-media', `${normalizePath(folder)}/${fileName}`)
}

export const vehicleAssetsIn = (...folders) => Object.entries(vehicleImages)
  .filter(([key]) => folders.some((folder) => key.startsWith(`./local/vehicle-media/${folder}/`.normalize('NFC'))))
  .map(([key, src]) => {
    const path = key.replace('./local/vehicle-media/', '').normalize('NFC')
    return {
      src: src || cdnUrl('vehicle-media', path),
      path,
    }
  })

export const commonMedia = {
  afterSalesConsultation: commonImage('after-sales-consultation.webp'),
  afterSalesHero: commonImage('after-sales-hero.webp'),
  limoGreenStudio: commonImage('limo-green-studio.webp'),
  nerioGreenStudio: commonImage('nerio-green-studio.png'),
  vfMpv7ModelCutout: commonImage('vf-mpv-7-model-cutout.png'),
  vf6FrontModelCutout: commonImage('vf6-front-model-cutout.png'),
  vf6ModelCutout: commonImage('vf6-model-cutout.png'),
  vf6Studio: commonImage('vf6-studio.webp'),
  vf9Studio: commonImage('vf9-studio.png'),
  vinfastLogo: commonImage('vinfast-logo.png'),
  vinfastRoadBanner: commonImage('vinfast-road-banner.webp'),
  viviAvatar: commonImage('vivi-avatar.png'),
  viviPortrait: commonImage('vivi-portrait-cutout.png'),
}
