/**
 * context/BackendStatusContext.jsx — Theo dõi backend còn sống hay không, cho cả site dùng chung.
 *
 * Cách hoạt động: ping GET /api/v1/booking/health ngay khi mở web, rồi LẶP LẠI MỖI 30 GIÂY.
 * Cũng lắng nghe sự kiện online/offline của trình duyệt.
 *
 * Trạng thái trả về (bookingStatus): 'checking' → 'ready' hoặc 'unavailable'.
 * Ai đang dùng:
 * - App.jsx: cung cấp trạng thái chung mà không chặn nội dung marketing.
 * - AppShell.jsx: 'unavailable' hiện dải băng vàng cảnh báo trên đầu trang.
 * - BookingPage.jsx: khoá các nút đặt lịch khi backend chết.
 *
 * Sửa ở đây khi: muốn đổi nhịp kiểm tra 30 giây, hoặc đổi cách xử lý khi mất kết nối.
 */
import { createContext, useContext, useEffect, useState } from 'react'
import { getBookingHealth } from '../api/availability'

const BackendStatusContext = createContext({ bookingStatus: 'checking', retry: () => {} })

export function BackendStatusProvider({ children }) {
  const [bookingStatus, setBookingStatus] = useState('checking')
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    let active = true
    const check = () => getBookingHealth()
      .then(() => { if (active) setBookingStatus('ready') })
      .catch(() => { if (active) setBookingStatus('unavailable') })

    check()
    const interval = window.setInterval(check, 30000)
    window.addEventListener('online', check)
    const offline = () => setBookingStatus('unavailable')
    window.addEventListener('offline', offline)
    return () => {
      active = false
      window.clearInterval(interval)
      window.removeEventListener('online', check)
      window.removeEventListener('offline', offline)
    }
  }, [retryKey])

  return (
    <BackendStatusContext.Provider value={{
      bookingStatus,
      retry: () => { setBookingStatus('checking'); setRetryKey((key) => key + 1) },
    }}>
      {children}
    </BackendStatusContext.Provider>
  )
}

export const useBackendStatus = () => useContext(BackendStatusContext)
