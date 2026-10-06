/**
 * components/booking/BookingHeader.jsx
 *
 * Top bar header for the booking studio:
 * - Link back to home
 * - VinFast Brand logo
 * - Session progress indicator
 */
import { Link } from 'react-router-dom'
import { ArrowLeft, ShieldCheck } from '@phosphor-icons/react'
import { Brand } from '../Brand'

export function BookingHeader() {
  return (
    <header className="booking-topbar booking-topbar--studio">
      <Link to="/"><ArrowLeft size={17} weight="light" /> Trang chủ</Link>
      <Brand />
      <div className="booking-topbar__persist">
        <ShieldCheck size={15} weight="light" aria-hidden="true" />
        Tiến trình được giữ trên thiết bị
      </div>
    </header>
  )
}
