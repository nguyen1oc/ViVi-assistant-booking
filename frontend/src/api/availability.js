/**
 * api/availability.js — Kiểm tra dịch vụ đặt lịch của backend còn sống hay không.
 *
 * Gọi tới: GET /api/v1/booking/health
 *
 * Chỉ có đúng một hàm getBookingHealth(). Nó được BackendStatusContext gọi lại mỗi 30 giây;
 * hỏng thì App.jsx chặn cả site và AppShell hiện dải băng vàng "Không thể kết nối backend".
 *
 * Cố ý TẮT fallbackToCache: kiểm tra sức khoẻ phải hỏi thật, không được trả lời bằng cache cũ.
 */
import { apiGet } from './client'

export const getBookingHealth = (options = {}) => apiGet('/booking/health', {
  ...options,
  cacheKey: 'booking-health',
  fallbackToCache: false,
})
