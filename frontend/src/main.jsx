/**
 * main.jsx — Điểm khởi động của toàn bộ frontend (entry point của Vite).
 *
 * Đây là file chạy ĐẦU TIÊN khi mở web: gắn React vào thẻ <div id="root"> trong index.html.
 *
 * Chứa gì:
 * - Nạp font toàn site: Geist Variable (tiêu đề, có subset tiếng Việt) và
 *   Be Vietnam Pro 400/500/600/700 (nội dung, microcopy tiếng Việt).
 * - Nạp index.css — toàn bộ style của website.
 * - Bọc <App /> trong AppErrorBoundary (màn hình lỗi khi React render hỏng) và React.StrictMode.
 *
 * Sửa ở đây khi: đổi font dùng chung, hoặc thêm thư viện/provider chạy bao trùm mọi trang.
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { AppErrorBoundary } from './components/AppErrorBoundary.jsx'
import '@fontsource-variable/geist'
import '@fontsource/be-vietnam-pro/400.css'
import '@fontsource/be-vietnam-pro/500.css'
import '@fontsource/be-vietnam-pro/600.css'
import '@fontsource/be-vietnam-pro/700.css'
import './index.css'

// Tắt scroll restoration ngay trước khi React mount. Nếu chờ router render xong,
// Safari có thể đã phục hồi vị trí cũ vào giữa video của trang chủ.
if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual'
if (window.location.pathname === '/' && !window.location.hash) window.scrollTo(0, 0)
window.addEventListener('pageshow', () => {
  if (window.location.pathname === '/' && !window.location.hash) {
    window.requestAnimationFrame(() => window.scrollTo(0, 0))
  }
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary><App /></AppErrorBoundary>
  </React.StrictMode>,
)
