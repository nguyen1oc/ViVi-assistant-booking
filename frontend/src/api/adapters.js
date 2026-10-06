/**
 * api/adapters.js — Phiên dịch dữ liệu backend sang đúng tên trường mà giao diện đang dùng.
 *
 * Lý do tồn tại: backend trả `bodyType`, `displayPrice`, `thumbnail.url`… còn các trang được
 * viết từ trước với `body`, `price`, `hero`. File này ngồi giữa để KHÔNG phải sửa lại JSX.
 * Backend đổi tên trường thì chỉ cần sửa ở đây, không cần đụng vào các trang.
 *
 * Chứa gì:
 * - mediaView(): gom một ảnh thành { src, alt, focalPoint, aspectRatio, fit } cho <SmartImage>.
 * - vehicleSummaryToCar(): dữ liệu xe rút gọn → thẻ xe ở trang chủ, menu, bảng đổi xe.
 * - vehicleDetailToCar(): thêm mô tả, brochure, bảng màu, chapters, gallery, video giới thiệu,
 *   ảnh motion (ảnh tách nền dùng cho animation xe chạy ở trang chi tiết).
 *
 * Sửa ở đây khi: giao diện thiếu một trường dữ liệu, hoặc backend đổi tên trường trong API.
 */
import { modelImage, vehicleImage } from '../media/assets'
import { withSupplementalColors } from '../data/vehicle-colors'
import { vehiclePrice } from '../data/vehicle-prices'

const vehicleMediaPrefix = '/media/vehicle-media/'
const catalogueVehicleMediaPattern = /\/media\/vehicles\/([^/?]+)\/(?:thumbnail|studio)\.[^/?#]+/i

const resolveVehicleMedia = (url = '') => {
  const catalogueMatch = url.match(catalogueVehicleMediaPattern)
  if (catalogueMatch) {
    return modelImage(decodeURIComponent(catalogueMatch[1])) || url
  }

  const markerIndex = url.indexOf(vehicleMediaPrefix)
  if (markerIndex === -1) return url
  const relativePath = decodeURI(url.slice(markerIndex + vehicleMediaPrefix.length))
  return vehicleImage(relativePath) || url
}

const mediaView = (media) => ({
  src: resolveVehicleMedia(media?.url || ''),
  alt: media?.alt || '',
  focalPoint: media?.focalPoint || '50% 50%',
  aspectRatio: media?.aspectRatio,
  fit: media?.fit,
})

const catalogueFact = (fact) => (
  fact?.label && fact?.value !== null && fact?.value !== undefined
    ? { label: String(fact.label), value: String(fact.value) }
    : null
)

const hexColorPattern = /^#[0-9a-f]{6}$/i
const catalogueColors = (colors) => (Array.isArray(colors) ? colors : [])
  .filter((color) => color?.name && hexColorPattern.test(color?.hex || ''))
  .map((color) => ({
    name: String(color.name),
    hex: color.hex,
    secondaryHex: hexColorPattern.test(color.secondaryHex || '') ? color.secondaryHex : null,
  }))

const productFacts = (items) => (Array.isArray(items) ? items : [])
  .filter((item) => item?.label && item?.value !== null && item?.value !== undefined)
  .map(({ label, value }) => ({ label: String(label), value: String(value) }))

export const vehicleSummaryToCar = (vehicle) => {
  const officialPrice = vehiclePrice(vehicle.id)

  return {
    id: vehicle.id,
    name: vehicle.name,
    navName: vehicle.navName,
    category: vehicle.category,
    body: vehicle.bodyType,
    seats: Number.isFinite(vehicle.seats) ? `${vehicle.seats} chỗ` : null,
    // Giá chính thức ở frontend chỉ ghi đè những mẫu có trong tài liệu nguồn.
    // Các mẫu chưa công bố giá giữ nguyên chuỗi catalogue/backend hiện tại.
    price: officialPrice ? `Giá niêm yết từ ${officialPrice.from}` : vehicle.displayPrice || null,
    priceFrom: officialPrice?.from || null,
    priceVariants: officialPrice?.variants || null,
    tagline: vehicle.tagline,
    hero: mediaView(vehicle.thumbnail).src,
    heroMedia: mediaView(vehicle.thumbnail),
    intro: mediaView(vehicle.thumbnail).src,
    studioShot: {
      ...mediaView(vehicle.studioImage),
      mode: vehicle.studioImage?.mode || 'photo',
    },
    specs: productFacts(vehicle.shortSpecs),
    highlights: productFacts(vehicle.shortSpecs),
    // TODO(BE): Populate these lightweight summary fields from GET /vehicles so
    // the homepage can show range, charging and colors without detail N+1 calls.
    // Contract and acceptance criteria: frontend/BACKEND_TODO.md.
    range: catalogueFact(vehicle.range),
    charging: catalogueFact(vehicle.charging),
    colorOptions: catalogueColors(vehicle.colorOptions),
    featured: vehicle.featured,
    testDriveEligible: vehicle.testDriveEligible,
    sortOrder: vehicle.sortOrder,
  }
}

export const vehicleDetailToCar = (vehicle) => {
  const specificationGroups = (Array.isArray(vehicle.specifications) ? vehicle.specifications : [])
    .map((group) => ({
      title: group?.group || 'Thông số',
      items: productFacts(group?.items),
    }))
    .filter((group) => group.items.length > 0)
  const fallbackSpecs = productFacts(vehicle.shortSpecs)
  const specs = specificationGroups.length
    ? specificationGroups.flatMap((group) => group.items)
    : fallbackSpecs

  return {
    ...vehicleSummaryToCar(vehicle),
    description: vehicle.description,
    brochure: vehicle.brochure,
    specs,
    specificationGroups: specificationGroups.length
      ? specificationGroups
      : fallbackSpecs.length
        ? [{ title: 'Thông số chính', items: fallbackSpecs }]
        : [],
    // Backend trả rỗng cho 8/14 mẫu; vá bằng bảng màu chính hãng ở data/vehicle-colors.js.
    // withSupplementalColors chỉ nhảy vào khi backend KHÔNG có màu nào, không bao giờ ghi đè.
    colors: withSupplementalColors(
      vehicle.id,
      (vehicle.colors || []).map((color) => ({ ...color, image: resolveVehicleMedia(color.image?.url || '') })),
    ),
    chapters: (vehicle.chapters || []).map((chapter) => ({
      ...chapter,
      ...mediaView(chapter.media),
    })),
    // TODO(BE): Return a semantic sectionKey for gallery items and films so the
    // detail IA can place them without filename/index inference. See BACKEND_TODO.md.
    gallery: (vehicle.gallery || []).map((media, index) => ({
      ...mediaView(media),
      sectionKey: media.sectionKey || null,
      label: media.title || `Góc nhìn ${String(index + 1).padStart(2, '0')}`,
      sortOrder: media.sortOrder ?? index,
    })),
    actionMedia: mediaView(vehicle.actionMedia),
    presentationFilm: vehicle.presentationFilm ? {
      src: vehicle.presentationFilm.url,
      poster: resolveVehicleMedia(vehicle.presentationFilm.posterUrl || ''),
      mimeType: vehicle.presentationFilm.mimeType,
      eyebrow: vehicle.presentationFilm.eyebrow,
      title: vehicle.presentationFilm.title,
      copy: vehicle.presentationFilm.copy,
      sectionKey: vehicle.presentationFilm.sectionKey || null,
    } : null,
    motionImage: resolveVehicleMedia(vehicle.motion?.imageUrl || ''),
  }
}
