/**
 * data/media.js — Danh sách ảnh/video MARKETING được đặt tên, dùng cho trang chủ và ViVi.
 *
 * Đây là chỗ tra "ảnh này lấy từ file nào" khi muốn thay ảnh trang chủ:
 * - factoryFilm       → video dây chuyền nhà máy (khối "factory-film" trang chủ).
 * - factoryAerial     → ảnh toàn cảnh nhà máy (khối "factory-origin").
 * - roadBanner        → ảnh xe trên đường (khối "road-chapter").
 * - vf9Sculpture      → ảnh VF 9 trong mục giới thiệu.
 * - viviPortrait      → ảnh ViVi cỡ lớn ở khối giới thiệu trợ lý trang chủ.
 * - viviAvatar        → ảnh đại diện ViVi nhỏ, hiện cạnh mỗi tin nhắn trong khung chat.
 * - limoInteriorFilm  → video nội thất Limo Green, chỉ hiện ở trang chi tiết xe limo-green.
 *
 * Thay ảnh: bỏ file mới vào src/media/local/ rồi đổi tên file trong các dòng bên dưới.
 * Các file này nhúng thẳng vào bundle nên luôn hiển thị được, kể cả khi backend chưa publish media.
 */
import { commonMedia, vehicleImage, vehicleVideo } from '../media/assets'

const factoryFilm = vehicleVideo('Video chính.mp4')
const limoInteriorFilm = vehicleVideo('Dịch vụ_Limo Green/Limo Green_Spacious Interior.mp4')
// Chân dung lớn đã tách alpha thật; không dùng lại JPEG nền trắng vì sẽ lộ khung ảnh.
const viviPortrait = commonMedia.viviPortrait
const viviAvatar = commonMedia.viviAvatar
const roadBanner = commonMedia.vinfastRoadBanner
const factoryAerial = vehicleImage('nha-may-vinfast.jpg')
const vf9Sculpture = vehicleImage('about-us.png.webp')

// TODO [BACKEND/CDN]: Replace bundled marketing media with the published media
// payload from GET /api/v1/content/home and GET /api/v1/vehicles/{id}/media.
// Video records must include url, posterUrl, mimeType, width, height, duration,
// autoplayAllowed and revision; image records need alt, focalPoint and revision.
// Keep these local imports as the offline/build-time fallback.
export {
  factoryAerial,
  factoryFilm,
  limoInteriorFilm,
  roadBanner,
  vf9Sculpture,
  viviAvatar,
  viviPortrait,
}
