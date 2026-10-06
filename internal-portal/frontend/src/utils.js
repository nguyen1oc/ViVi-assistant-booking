export const roleLabels = {
  staff: 'Nhân viên tư vấn',
  showroom_manager: 'Quản lý showroom',
  operations_admin: 'Operations Admin',
}

export const statusLabels = {
  held: 'Đang giữ',
  confirmed: 'Đã xác nhận',
  checked_in: 'Đã check-in',
  completed: 'Hoàn tất',
  no_show: 'Không đến',
  cancelled: 'Đã hủy',
  rescheduled: 'Đã đổi lịch',
  expired: 'Hết hạn',
  available: 'Sẵn sàng',
  booked: 'Đã đặt',
  blocked: 'Đã khóa',
  charging: 'Đang sạc',
  maintenance: 'Bảo trì',
  out_of_service: 'Ngừng phục vụ',
  in_use: 'Đang sử dụng',
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' }).format(
    new Date(value),
  )
}

export function actionId(prefix) {
  return `${prefix}:${crypto.randomUUID()}`
}
