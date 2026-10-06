import {
  ArrowRight,
  ArrowsClockwise,
  CalendarBlank,
  CarProfile,
  MagnifyingGlass,
  X,
} from '@phosphor-icons/react'
import { useDialogFocus } from '../../hooks/useDialogFocus'

const ACTIONS = [
  {
    id: 'calendar',
    label: 'Thêm vào lịch',
    description: 'Lưu buổi lái thử vào lịch trên thiết bị',
    icon: CalendarBlank,
    requiresConfirmedBooking: true,
  },
  {
    id: 'manage',
    label: 'Đổi hoặc huỷ lịch',
    description: 'Xác thực OTP để thay đổi lịch đã đặt',
    icon: ArrowsClockwise,
  },
  {
    id: 'another',
    label: 'Đặt thêm mẫu xe khác',
    description: 'Giữ lịch hiện tại và bắt đầu một lịch mới',
    icon: CarProfile,
    requiresConfirmedBooking: true,
  },
  {
    id: 'lookup',
    label: 'Tra cứu lịch',
    description: 'Xem các lịch hợp lệ theo email đăng ký',
    icon: MagnifyingGlass,
  },
]

export function BookingActionMenu({
  open,
  onClose,
  hasConfirmedBooking,
  onAddToCalendar,
  onManageBooking,
  onBookAnother,
  onLookup,
}) {
  const dialogRef = useDialogFocus({ active: open, onClose })

  if (!open) return null

  const handlers = {
    calendar: onAddToCalendar,
    manage: onManageBooking,
    another: onBookAnother,
    lookup: onLookup,
  }

  const runAction = (id) => {
    onClose()
    handlers[id]?.()
  }

  return (
    <div
      className="booking-action-menu"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <section
        ref={dialogRef}
        className="booking-action-menu__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="booking-action-menu-title"
        tabIndex={-1}
      >
        <header className="booking-action-menu__header">
          <div>
            <span>Quản lý lịch lái thử</span>
            <h2 id="booking-action-menu-title">Bạn muốn thực hiện thao tác nào?</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Đóng menu thao tác">
            <X size={18} weight="light" aria-hidden="true" />
          </button>
        </header>

        <div className="booking-action-menu__list">
          {ACTIONS.map((action) => {
            const disabled = action.requiresConfirmedBooking && !hasConfirmedBooking
            const Icon = action.icon

            return (
              <button
                key={action.id}
                type="button"
                disabled={disabled}
                onClick={() => runAction(action.id)}
              >
                <span className="booking-action-menu__icon">
                  <Icon size={20} weight="light" aria-hidden="true" />
                </span>
                <span className="booking-action-menu__copy">
                  <strong>{action.label}</strong>
                  <small>{disabled ? 'Có sau khi lịch được xác nhận' : action.description}</small>
                </span>
                <ArrowRight size={17} weight="light" aria-hidden="true" />
              </button>
            )
          })}
        </div>

        <p>Các thao tác xem, đổi hoặc huỷ lịch sẽ yêu cầu xác thực OTP.</p>
      </section>
    </div>
  )
}
