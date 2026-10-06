/**
 * utils/scrollToTop.js — đưa trang về đầu.
 *
 * Dùng chung cho logo VinFast (components/Brand.jsx) và nút mũi tên lên
 * (components/BackToTop.jsx). Tách ra vì hai chỗ phải hành xử giống hệt nhau:
 * cùng kiểu cuộn, cùng cách buông điểm cuộn đã ghi trong history, cùng cách trả
 * tiêu điểm bàn phím về đầu nội dung.
 *
 * KHÁC với nút Back của trình duyệt — đừng gộp hai thứ này làm một:
 * - Back  → phục hồi đúng chỗ người dùng đang đứng trước khi mở trang xe.
 *           Logic đó nằm ở RouteEffects trong App.jsx.
 * - Logo / nút mũi tên → luôn về đầu trang, bất kể trước đó đang ở đâu.
 */

/**
 * History entry của trang chủ có thể đang giữ `restoreScrollY` do RouteEffects ghi
 * lại lúc người dùng bấm vào một mẫu xe (App.jsx). Đó là dữ liệu dành cho nút Back.
 * Khi người dùng chủ động về đầu trang thì điểm cũ hết ý nghĩa — giữ lại thì lần
 * Back sau sẽ ném họ về đúng chỗ vừa cố ý rời bỏ.
 */
function forgetRememberedScroll() {
  const historyState = window.history.state
  const userState = historyState?.usr
  if (!userState || typeof userState !== 'object') return
  if (!Object.hasOwn(userState, 'restoreScrollY')) return

  const { restoreScrollY: _dropped, preserveScrollRestore: _flag, ...rest } = userState
  window.history.replaceState({ ...historyState, usr: rest }, '')
}

export function scrollPageToTop({ smooth = true } = {}) {
  forgetRememberedScroll()

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: smooth && !reducedMotion ? 'smooth' : 'instant' })

  // Cuộn không kéo theo tiêu điểm bàn phím. Không trả tiêu điểm về đầu thì người dùng
  // bàn phím bấm nút xong màn hình lên đầu trang nhưng Tab kế tiếp lại nhảy ngược
  // xuống giữa trang. tabindex gỡ ngay khi mất tiêu điểm để <main> không nằm trong
  // thứ tự Tab thường ngày.
  const main = document.getElementById('main-content')
  if (!main) return

  main.setAttribute('tabindex', '-1')
  main.focus({ preventScroll: true })
  main.addEventListener('blur', () => main.removeAttribute('tabindex'), { once: true })
}
