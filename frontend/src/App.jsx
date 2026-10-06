/**
 * App.jsx — Bộ định tuyến (router) của toàn site + cổng kiểm tra backend.
 *
 * Quyết định URL nào hiện trang nào, đồng thời chia sẻ trạng thái backend cho toàn site.
 *
 * Chứa gì:
 * - Bảng route:  "/" → HomePage  ·  "/models/:carId" → CarDetailPage  ·  "/booking" → BookingPage
 *                "/after-sales" → AfterSalesPage  ·  "/charging" → ChargingPage
 * - Route tương thích: "/agent" → /booking (giữ query/hash) · "/home" → "/".
 *   URL lạ hiển thị trang 404 có đường quay lại rõ ràng.
 * - BackendStatusProvider: cho phép các trang marketing vẫn hiển thị ở degraded mode khi backend lỗi;
 *   booking tự khóa thao tác phụ thuộc API, còn AppShell hiện banner thử kết nối lại.
 * - RouteEffects: route mới cuộn lên đầu, URL có #anchor cuộn tới đúng mục, còn Back/Forward
 *   từ trang chi tiết xe phục hồi chính xác vị trí người dùng đang xem trên trang chủ.
 *
 * Sửa ở đây khi: thêm/đổi đường dẫn trang, hoặc sửa giao diện 2 màn hình chờ/lỗi backend.
 */
import { useLayoutEffect } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { CarDetailPage } from './pages/CarDetailPage'
import { BookingPage } from './pages/BookingPage'
import { AfterSalesPage } from './pages/AfterSalesPage'
import { ChargingPage } from './pages/ChargingPage'
import { InvitationPage, InvitationPreviewPage } from './pages/InvitationPreviewPage'
import { InvitationEmailPreviewPage } from './pages/InvitationEmailPreviewPage'
import { BackendStatusProvider } from './context/BackendStatusContext'
import { rememberBookingReturnContext } from './utils/bookingReturnContext'
import { AppShell } from './components/AppShell'
import { IslandButton } from './components/IslandButton'

function LegacyAgentRedirect() {
  const location = useLocation()
  return <Navigate to={{ pathname: '/booking', search: location.search, hash: location.hash }} replace />
}

function NotFoundPage() {
  return (
    <AppShell>
      <main id="main-content" className="not-found">
        <div className="not-found__inner">
          <p className="eyebrow">Không tìm thấy trang</p>
          <h1>Đường dẫn này không tồn tại.</h1>
          <p>Địa chỉ có thể đã thay đổi hoặc liên kết bạn mở không còn hợp lệ.</p>
          <IslandButton to="/" variant="dark">Về trang chủ</IslandButton>
        </div>
      </main>
    </AppShell>
  )
}

// TODO [BACKEND/DEPLOY]: BrowserRouter requires the production web server to
// return index.html for every non-file route (/cars/:id, /booking). Keep /api
// outside this fallback and proxy it to the backend. See ../BACKEND_HANDOFF.md.
function RouteEffects() {
  const location = useLocation()

  useLayoutEffect(() => {
    const rememberNavigationOrigin = (event) => {
      const anchor = event.target.closest?.('a[href]')
      if (!anchor || anchor.hasAttribute('download')) return
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
      if (anchor.target && anchor.target !== '_self') return

      const destination = new URL(anchor.href, window.location.href)
      if (destination.origin !== window.location.origin) return

      if (destination.pathname === '/booking' && location.pathname !== '/booking') {
        rememberBookingReturnContext({
          pathname: location.pathname,
          search: location.search,
          hash: location.hash,
          scrollY: window.scrollY,
        })
      }

      // Ghi vị trí vào CHÍNH history entry của trang chủ. Khi người dùng bấm Back,
      // React Router quay lại entry này và RouteEffects có đủ dữ liệu để phục hồi đúng
      // điểm đã bấm, kể cả catalogue/ảnh làm chiều cao trang xuất hiện trễ.
      const opensVehicleDetail = /^\/(?:models|cars)\/[^/]+\/?$/.test(destination.pathname)
      if (location.pathname === '/' && opensVehicleDetail) {
        const currentHistoryState = window.history.state || {}
        const currentUserState = currentHistoryState.usr && typeof currentHistoryState.usr === 'object'
          ? currentHistoryState.usr
          : {}

        window.history.replaceState({
          ...currentHistoryState,
          usr: {
            ...currentUserState,
            restoreScrollY: Math.max(0, Math.round(window.scrollY)),
            preserveScrollRestore: true,
          },
        }, '')
      }
    }

    // Capture phase chạy trước React Router, nên scrollY vẫn là vị trí của trang nguồn.
    document.addEventListener('click', rememberNavigationOrigin, true)
    return () => document.removeEventListener('click', rememberNavigationOrigin, true)
  }, [location.pathname, location.search, location.hash])

  useLayoutEffect(() => {
    if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual'

    let secondFrame
    let hashObserver
    let hashTimeout
    let resizeObserver
    const firstFrame = window.requestAnimationFrame(() => {
      const restoreScrollY = Number(location.state?.restoreScrollY)
      if (Number.isFinite(restoreScrollY) && restoreScrollY >= 0) {
        // State do một nút điều hướng truyền trực tiếp chỉ dùng một lần; riêng history entry
        // của trang chủ giữ lại để chuỗi Back → Forward → Back vẫn phục hồi đúng vị trí.
        const currentHistoryState = window.history.state
        if (!location.state?.preserveScrollRestore && currentHistoryState?.usr && Object.hasOwn(currentHistoryState.usr, 'restoreScrollY')) {
          const { restoreScrollY: _consumedRestore, ...nextUserState } = currentHistoryState.usr
          window.history.replaceState({ ...currentHistoryState, usr: nextUserState }, '')
        }

        const stopRestoring = () => {
          resizeObserver?.disconnect()
          if (hashTimeout) window.clearTimeout(hashTimeout)
        }
        const restoreExactPosition = () => {
          const pageHeight = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)
          const maxScroll = Math.max(0, pageHeight - window.innerHeight)
          window.scrollTo({ top: Math.min(restoreScrollY, maxScroll), behavior: 'instant' })
          if (maxScroll >= restoreScrollY - 1 && Math.abs(window.scrollY - restoreScrollY) <= 2) {
            stopRestoring()
            return true
          }
          return false
        }

        if (!restoreExactPosition()) {
          // Trang chi tiết có dữ liệu/ảnh động. Theo dõi chiều cao cho tới khi điểm cũ tồn tại,
          // rồi dừng ngay để không giành quyền cuộn khỏi tay người dùng.
          if ('ResizeObserver' in window) {
            resizeObserver = new ResizeObserver(restoreExactPosition)
            resizeObserver.observe(document.documentElement)
          }
          hashTimeout = window.setTimeout(stopRestoring, 5000)
        }
        secondFrame = window.requestAnimationFrame(restoreExactPosition)
      } else if (location.hash) {
        const scrollToHash = () => {
          const target = document.getElementById(decodeURIComponent(location.hash.slice(1)))
          if (!target) return false
          target.scrollIntoView({ behavior: 'smooth', block: 'start' })
          hashObserver?.disconnect()
          if (hashTimeout) window.clearTimeout(hashTimeout)
          return true
        }

        // Catalogue/backend có thể trả về sau khi RouteEffects đã mount. Theo dõi DOM
        // trong thời gian ngắn để anchor của section động (như model 3D) vẫn hoạt động.
        if (!scrollToHash()) {
          hashObserver = new MutationObserver(scrollToHash)
          hashObserver.observe(document.body, { childList: true, subtree: true })
          hashTimeout = window.setTimeout(() => hashObserver?.disconnect(), 5000)
        }
      } else {
        window.scrollTo({ top: 0, behavior: 'instant' })
        // Safari đôi khi phục hồi vị trí cũ sau frame đầu. Frame thứ hai giữ chắc
        // màn hình mở đầu ở hero thay vì nhảy xuống video trong trang chủ.
        secondFrame = window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'instant' }))
      }
    })
    return () => {
      window.cancelAnimationFrame(firstFrame)
      if (secondFrame) window.cancelAnimationFrame(secondFrame)
      if (hashTimeout) window.clearTimeout(hashTimeout)
      hashObserver?.disconnect()
      resizeObserver?.disconnect()
    }
  }, [location.pathname, location.hash, location.state?.restoreScrollY])

  return null
}

function AppRoutes() {
  return (
    <>
      <RouteEffects />
      <Routes>
        <Route path="/invitation-preview" element={<InvitationPreviewPage />} />
        <Route path="/invitation-email-preview" element={<InvitationEmailPreviewPage />} />
        <Route path="/invitation/:token" element={<InvitationPage />} />
        <Route element={<BackendAwareRoutes />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/cars/:carId" element={<CarDetailPage />} />
          <Route path="/models/:carId" element={<CarDetailPage />} />
          <Route path="/booking" element={<BookingPage />} />
          <Route path="/after-sales" element={<AfterSalesPage />} />
          <Route path="/charging" element={<ChargingPage />} />
          <Route path="/agent" element={<LegacyAgentRedirect />} />
          <Route path="/home" element={<Navigate to="/" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </>
  )
}

function BackendAwareRoutes() {
  return (
    <BackendStatusProvider>
      <Outlet />
    </BackendStatusProvider>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}
