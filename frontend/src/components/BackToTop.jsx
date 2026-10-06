/**
 * components/BackToTop.jsx — nút mũi tên đưa trang về đầu, nổi ở góc phải dưới màn hình.
 *
 * Chỉ hiện sau khi người dùng đã lướt qua màn đầu tiên. Bấm vào cho kết quả GIỐNG HỆT
 * bấm logo VinFast — cả hai gọi chung scrollPageToTop() nên không thể lệch nhau.
 *
 * Đang gắn ở HomePage. KHÔNG đưa lên AppShell: trang chi tiết xe đã có .detail-booking-dock
 * (fixed, right 22px, bottom 22px) và .test-drive-nudge ở đúng góc đó, chồng lên nhau ngay.
 *
 * Ngưỡng hiện nút lấy theo chiều cao khung nhìn chứ không theo một con số pixel cố định,
 * vì hero trang chủ cao 100dvh — mỗi máy một khác.
 */
import { useEffect, useState } from 'react'
import { ArrowUp } from '@phosphor-icons/react'
import { scrollPageToTop } from '../utils/scrollToTop'

const LABEL = 'Về đầu trang'

export function BackToTop() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    let frame = 0

    const update = () => {
      frame = 0
      // 0,85 màn thay vì trọn 1 màn: nút xuất hiện ngay lúc hero rời khung nhìn,
      // không để người dùng phải cuộn thêm một đoạn nữa mới thấy.
      setVisible(window.scrollY > window.innerHeight * 0.85)
    }

    // Sự kiện scroll bắn rất dày; gom về mỗi frame một lần để không giành CPU
    // với các ScrollTrigger của trang chủ.
    const schedule = () => {
      if (frame) return
      frame = window.requestAnimationFrame(update)
    }

    update()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule, { passive: true })

    return () => {
      if (frame) window.cancelAnimationFrame(frame)
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
  }, [])

  return (
    <button
      type="button"
      className={`back-to-top ${visible ? 'is-visible' : ''}`}
      onClick={() => scrollPageToTop()}
      aria-label={LABEL}
      title={LABEL}
    >
      <ArrowUp size={20} weight="light" aria-hidden="true" />
    </button>
  )
}
