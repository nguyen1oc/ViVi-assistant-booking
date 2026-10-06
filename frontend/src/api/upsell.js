/**
 * api/upsell.js — Lấy CẤU HÌNH UPSELL mà sale admin chọn cho khung chat đặt lịch.
 *
 * Gọi tới: GET /api/v1/settings/booking-upsell
 *
 * Đây là ba mẫu xe showroom đang muốn đẩy. Khi khách mở thẳng ViVi mà chưa xem xe nào,
 * ViVi hỏi "bạn muốn lái thử mẫu nào" và ba mẫu này là thứ đầu tiên khách nhìn thấy.
 * Bên trang admin chỉ cần đổi 3 id trong cấu hình là màn đặt lịch đổi theo, không phải build lại.
 *
 * HỢP ĐỒNG DỮ LIỆU backend cần trả (chi tiết và tiêu chí nghiệm thu ở BACKEND_TODO.md):
 *   {
 *     "data": {
 *       "vehicleIds": ["vf9", "vf3", "vf8"],   // đúng 3 id, theo thứ tự admin xếp
 *       "headline": "Showroom đang ưu tiên",   // tuỳ chọn, để trống thì dùng mặc định
 *       "note": "Còn xe demo trong tuần này",  // tuỳ chọn, dòng phụ dưới tiêu đề
 *       "updatedAt": "2026-08-18T09:00:00Z"
 *     }
 *   }
 *
 * Backend chưa có endpoint này thì frontend dùng DEFAULT_UPSELL_VEHICLE_IDS. Đây KHÔNG phải
 * dữ liệu xe bịa ra: bản thân thông tin xe vẫn lấy từ GET /vehicles như cũ, ở đây chỉ là
 * giá trị mặc định của một tuỳ chọn cấu hình, nên vẫn giữ đúng nguyên tắc không chế dữ liệu.
 */
import { apiGet } from './client'

/** Số ô upsell hiển thị. Giao diện dựng theo lưới 3 cột, đổi số này phải sửa cả CSS. */
export const UPSELL_SLOT_COUNT = 3

/**
 * Mặc định khi admin chưa cấu hình: VF 9 (đầu bảng) → VF 3 (tệp phổ thông) → VF 8 (SUV chủ lực).
 * Từ 2 lên 3 ô ngày 18/08/2026 — hai ô kéo ngang cả khối trông lệch, ba ô cân hơn.
 * Thứ tự đổi ngày 28/08/2026 theo yêu cầu: mẫu đầu bảng đứng trước.
 *
 * THỨ TỰ Ở ĐÂY LÀ THỨ TỰ HIỂN THỊ. BookingPage map thẳng mảng này sang thẻ xe
 * (`upsell.vehicleIds.map(getCar)`), không sắp xếp lại theo catalogue.
 */
export const DEFAULT_UPSELL_VEHICLE_IDS = ['vf9', 'vf3', 'vf8']

export const getBookingUpsell = (options = {}) =>
  apiGet('/settings/booking-upsell', { ...options, cacheKey: 'settings:booking-upsell' })

/** Chuẩn hoá cấu hình admin gửi xuống: cắt đúng UPSELL_SLOT_COUNT slot, bỏ id trùng và rỗng. */
export const normalizeUpsellConfig = (payload) => {
  const ids = (Array.isArray(payload?.vehicleIds) ? payload.vehicleIds : [])
    .map((id) => String(id || '').trim().toLowerCase())
    .filter(Boolean)
  const unique = [...new Set(ids)].slice(0, UPSELL_SLOT_COUNT)
  return {
    vehicleIds: unique.length ? unique : DEFAULT_UPSELL_VEHICLE_IDS,
    headline: String(payload?.headline || '').trim(),
    note: String(payload?.note || '').trim(),
    updatedAt: payload?.updatedAt || '',
    configured: unique.length > 0,
  }
}
