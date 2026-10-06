/**
 * Lưu nơi người dùng đang đứng ngay trước khi mở luồng đặt lịch.
 *
 * Dùng sessionStorage thay vì localStorage để ngữ cảnh chỉ thuộc tab hiện tại. URL được
 * tách thành pathname/search/hash và kiểm tra lại khi đọc để không biến nút quay lại thành
 * một open redirect. Vị trí cuộn là số tuyệt đối vì yêu cầu là trở về đúng đoạn đang xem,
 * không chỉ về đầu trang chi tiết xe.
 */
const BOOKING_RETURN_CONTEXT_KEY = 'vinfast:booking-return-context:v1'
const BOOKING_RETURN_CONTEXT_TTL = 2 * 60 * 60 * 1000

const removeStoredContext = () => {
  try {
    window.sessionStorage.removeItem(BOOKING_RETURN_CONTEXT_KEY)
  } catch {
    // Trình duyệt chặn storage vẫn không được làm hỏng điều hướng chính.
  }
}

export const clearBookingReturnContext = removeStoredContext

export function rememberBookingReturnContext({ pathname, search = '', hash = '', scrollY = 0 }) {
  if (typeof window === 'undefined' || !pathname || pathname === '/booking') return

  try {
    window.sessionStorage.setItem(BOOKING_RETURN_CONTEXT_KEY, JSON.stringify({
      pathname,
      search,
      hash,
      scrollY: Math.max(0, Math.round(Number(scrollY) || 0)),
      capturedAt: Date.now(),
    }))
  } catch {
    // Safari private mode hoặc policy storage: nút back vẫn dùng fallback an toàn.
  }
}

export function takeBookingReturnContext() {
  if (typeof window === 'undefined') return null

  try {
    const raw = window.sessionStorage.getItem(BOOKING_RETURN_CONTEXT_KEY)
    removeStoredContext()
    if (!raw) return null

    const context = JSON.parse(raw)
    const pathname = typeof context.pathname === 'string' ? context.pathname : ''
    const search = typeof context.search === 'string' ? context.search : ''
    const hash = typeof context.hash === 'string' ? context.hash : ''
    const capturedAt = Number(context.capturedAt)
    const scrollY = Number(context.scrollY)

    if (!pathname.startsWith('/') || pathname.startsWith('//') || pathname === '/booking') return null
    if (!Number.isFinite(capturedAt) || Date.now() - capturedAt > BOOKING_RETURN_CONTEXT_TTL) return null

    return {
      href: `${pathname}${search}${hash}`,
      scrollY: Number.isFinite(scrollY) ? Math.max(0, scrollY) : 0,
    }
  } catch {
    removeStoredContext()
    return null
  }
}
