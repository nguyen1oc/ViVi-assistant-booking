/**
 * components/Reveal.jsx — Hiệu ứng "trồi lên khi cuộn tới" dùng chung cho các trang marketing.
 *
 * Bọc quanh khối nội dung nào thì khối đó mờ + nhoè + nằm thấp hơn 56px, khi cuộn tới
 * 88% chiều cao màn hình sẽ trồi lên rõ dần. Chỉ chạy MỘT LẦN (once: true), không lặp lại.
 *
 * Props: `as` đổi thẻ HTML (mặc định div) · `delay` trễ vài mili giây để tạo hiệu ứng
 * so le giữa nhiều khối · `y` khoảng cách trồi lên.
 *
 * Thông số animation (duration 1.05s, ease power4.out) nằm ngay trong file này.
 * Tôn trọng prefers-reduced-motion: máy bật giảm chuyển động thì hiện thẳng, không animate.
 *
 * Dùng ở: HomePage, CarDetailPage, AfterSalesPage, ChargingPage.
 * LƯU Ý: hiệu ứng phức tạp hơn (parallax, pin, scrub) được viết riêng trong từng trang, không ở đây.
 */
import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { getClientDeviceProfile } from '../utils/deviceProfile'

gsap.registerPlugin(useGSAP, ScrollTrigger)

export function Reveal({
  as: Tag = 'div',
  children,
  className = '',
  delay = 0,
  y = 56,
}) {
  const root = useRef(null)

  useGSAP(
    () => {
      const { compact, constrained, reducedMotion } = getClientDeviceProfile()
      if (reducedMotion || constrained) {
        gsap.set(root.current, { opacity: 1, y: 0, filter: 'none' })
        return
      }

      gsap.fromTo(
        root.current,
        {
          opacity: 0,
          y: compact ? Math.min(y, 24) : y,
          filter: compact ? 'none' : 'blur(10px)',
        },
        {
          opacity: 1,
          y: 0,
          filter: 'blur(0px)',
          duration: compact ? 0.48 : 1.05,
          delay: compact ? Math.min(delay, 0.08) : delay,
          ease: compact ? 'power3.out' : 'power4.out',
          scrollTrigger: {
            trigger: root.current,
            start: 'top 88%',
            once: true,
          },
        },
      )
    },
    { scope: root, dependencies: [delay, y] },
  )

  return (
    <Tag ref={root} className={`reveal-shell ${className}`.trim()}>
      {children}
    </Tag>
  )
}
