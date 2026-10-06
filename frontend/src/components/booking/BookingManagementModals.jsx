/**
 * components/booking/BookingManagementModals.jsx — 2 hộp thoại xác nhận khi sửa lịch đã đặt.
 *
 * ✅ ĐANG DÙNG THẬT: BookingPage.jsx render cả hai (~dòng 1788 và 1790).
 *
 * - CancellationConfirmModal: "Bạn muốn huỷ lịch <mã>?" — hiện ảnh xe + 7 dòng thông tin,
 *   2 nút "Xác nhận huỷ lịch" / "Giữ lại lịch".
 * - RescheduleConfirmModal: xác nhận đổi sang khung giờ mới, có ĐỒNG HỒ ĐẾM NGƯỢC thời gian
 *   giữ chỗ. Hết giờ (secondsLeft <= 0) thì nút xác nhận tự khoá.
 *
 * Ngày giờ được format bằng toLocaleDateString('vi-VN') — thứ, ngày/tháng, giờ 24h.
 * Style tương ứng: .slot-confirm-modal và .cancellation-confirm-modal trong index.css.
 */
import { X } from '@phosphor-icons/react'
import { VehicleShot } from './VehicleWorkspace'
import { useDialogFocus } from '../../hooks/useDialogFocus'

export function CancellationConfirmModal({ profile, car, onConfirm, onClose, busy, error }) {
  const rows = [['Người đặt lịch', profile.bookerName], ['Người lái thử', profile.driverName], ['Điện thoại', profile.phone], ['Email', profile.email], ['Mẫu xe', profile.vehicleName], ['Showroom', profile.showroomName], ['Thời gian', `${profile.slotTime} · ${profile.slotDate}`]]
  const dialogRef = useDialogFocus({ onClose })
  return (
    <div ref={dialogRef} className="slot-confirm-modal cancellation-confirm-modal" role="dialog" aria-modal="true" aria-labelledby="cancellation-confirm-title" tabIndex={-1}>
      <div>
        <button type="button" onClick={onClose} aria-label="Đóng"><X size={17} weight="light" /></button>
        <p>Kiểm tra trước khi hủy lịch</p>
        <div className="cancellation-confirm-modal__vehicle">{car && <VehicleShot car={car} className="cancellation-confirm-modal__image" eager />}<div><strong>{profile.vehicleName}</strong><small>{car?.body || 'Lái thử VinFast'}</small></div></div>
        <h2 id="cancellation-confirm-title">Bạn muốn hủy lịch {profile.bookingCode}?</h2>
        <dl>{rows.map(([label, detail]) => <div key={label}><dt>{label}</dt><dd>{detail || '—'}</dd></div>)}</dl>
        {error && <small className="booking-api-error" role="alert">{error}</small>}
        <div className="slot-confirm-actions"><button type="button" onClick={onConfirm} disabled={busy} className="cancellation-confirm-modal__submit">Xác nhận hủy lịch</button><button type="button" onClick={onClose}>Giữ lại lịch</button></div>
      </div>
    </div>
  )
}

export function RescheduleConfirmModal({ state, secondsLeft, onConfirm, onBack, busy }) {
  const startsAt = new Date(state.slot.start_at)
  const time = startsAt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false })
  const dialogRef = useDialogFocus({ onClose: onBack })
  return (
    <div ref={dialogRef} className="slot-confirm-modal" role="dialog" aria-modal="true" aria-labelledby="reschedule-confirm-title" tabIndex={-1}>
      <div>
        <button type="button" onClick={onBack} aria-label="Đóng"><X size={17} weight="light" /></button>
        <div className="slot-confirm-summary"><span>{startsAt.toLocaleDateString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' })}</span><strong>{time}</strong></div>
        <p aria-live="polite">Xác nhận đổi khung giờ · còn {Math.floor(secondsLeft / 60)}:{String(secondsLeft % 60).padStart(2, '0')}</p>
        <h2 id="reschedule-confirm-title">Bạn sẽ lái thử {state.car.name}</h2>
        <dl><div><dt>Showroom</dt><dd>{state.showroom.name}</dd></div><div><dt>Thời gian</dt><dd>{startsAt.toLocaleString('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</dd></div><div><dt>Mẫu xe</dt><dd>{state.car.name} đã được giữ cho slot này</dd></div></dl>
        <div className="slot-confirm-actions"><button type="button" onClick={onConfirm} disabled={busy || secondsLeft <= 0}>Xác nhận đổi lịch</button><button type="button" onClick={onBack}>Quay lại phiếu lịch</button></div>
      </div>
    </div>
  )
}
