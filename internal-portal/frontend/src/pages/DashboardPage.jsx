import { CalendarCheck, CarProfile, CheckCircle, Clock, Storefront, UsersThree } from '@phosphor-icons/react'
import { useEffect } from 'react'
import { api } from '../api.js'
import { PageState } from '../components/PageState.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'
import { useRemote } from '../hooks.js'
import { formatDateTime, statusLabels } from '../utils.js'

function Metric({ icon: Icon, label, value, note, tone }) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <div className="metric-card__icon"><Icon size={23} weight="duotone" /></div>
      <div><span>{label}</span><strong>{Number(value || 0).toLocaleString('vi-VN')}</strong><small>{note}</small></div>
    </article>
  )
}

function TrendChart({ points }) {
  const maximum = Math.max(...points.map((point) => point.total), 1)
  return (
    <>
      <div className="chart-legend">
        <span><i className="legend-swatch legend-swatch--active" />Đang xử lý</span>
        <span><i className="legend-swatch legend-swatch--completed" />Hoàn tất</span>
        <span><i className="legend-swatch legend-swatch--no-show" />No-show</span>
        <span><i className="legend-swatch legend-swatch--cancelled" />Đã hủy</span>
      </div>
      <div className="pace-chart" aria-label="Nhịp lịch lái thử 14 ngày">
        {points.map((point) => {
          const resolved = point.completed + point.no_show + point.cancelled
          const active = Math.max(0, point.total - resolved)
          return (
            <div className="pace-chart__day" key={point.date} title={`${point.date}: ${point.total} booking`}>
              <strong>{point.total || ''}</strong>
              <div className="pace-chart__track">
                {point.total > 0 && (
                  <div className="pace-chart__bar" style={{ height: `${Math.max((point.total / maximum) * 100, 5)}%` }}>
                    {active > 0 && <span className="pace-chart__active" style={{ flex: active }} />}
                    {point.completed > 0 && <span className="pace-chart__completed" style={{ flex: point.completed }} />}
                    {point.no_show > 0 && <span className="pace-chart__no-show" style={{ flex: point.no_show }} />}
                    {point.cancelled > 0 && <span className="pace-chart__cancelled" style={{ flex: point.cancelled }} />}
                  </div>
                )}
              </div>
              <span>{new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit' }).format(new Date(`${point.date}T00:00:00`))}</span>
            </div>
          )
        })}
      </div>
    </>
  )
}

function CapacityChart({ points }) {
  const booked = points.reduce((sum, point) => sum + point.booked, 0)
  const usable = points.reduce((sum, point) => sum + point.total - point.blocked, 0)
  const utilization = usable ? Math.round((booked / usable) * 100) : 0
  return (
    <>
      <div className="capacity-summary">
        <strong>{utilization}%</strong>
        <span>{booked.toLocaleString('vi-VN')} / {usable.toLocaleString('vi-VN')} slot khả dụng đã được đặt</span>
      </div>
      <div className="capacity-list">
        {points.map((point) => {
          const denominator = Math.max(point.total, 1)
          return (
            <div className="capacity-row" key={point.date}>
              <span>{new Intl.DateTimeFormat('vi-VN', { weekday: 'short', day: '2-digit', month: '2-digit' }).format(new Date(`${point.date}T00:00:00`))}</span>
              <div className="capacity-track">
                <i className="capacity-track__booked" style={{ width: `${point.booked * 100 / denominator}%` }} />
                <i className="capacity-track__blocked" style={{ width: `${point.blocked * 100 / denominator}%` }} />
              </div>
              <strong>{point.utilization_percent}%</strong>
            </div>
          )
        })}
      </div>
      <div className="chart-legend chart-legend--compact">
        <span><i className="legend-swatch legend-swatch--booked" />Đã đặt</span>
        <span><i className="legend-swatch legend-swatch--blocked" />Tạm khóa</span>
      </div>
    </>
  )
}

export function DashboardPage({ token, user }) {
  const state = useRemote(() => api.dashboard(token), [token])
  const data = state.data || {}
  const bookingTotal = Object.values(data.booking_counts || {}).reduce((sum, value) => sum + value, 0)
  const maxBooking = Math.max(...Object.values(data.booking_counts || {}), 1)
  useEffect(() => {
    const refresh = () => state.reload({ silent: true })
    const timer = window.setInterval(refresh, 30_000)
    window.addEventListener('focus', refresh)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', refresh)
    }
  }, [state.reload])
  const metrics = user.role === 'staff'
    ? [
        { icon: CalendarCheck, label: 'Booking hôm nay', value: data.bookings_today, note: 'Chỉ booking được phân công', tone: 'blue' },
        { icon: CheckCircle, label: 'Booking sắp tới', value: data.upcoming_bookings, note: `${bookingTotal} booking trong phạm vi của tôi`, tone: 'green' },
        { icon: Clock, label: 'Ca làm của tôi', value: data.scheduled_shift_total, note: 'Ca đang được xếp', tone: 'orange' },
        { icon: Storefront, label: 'Showroom', value: data.showroom_total, note: 'Nơi làm việc hiện tại', tone: 'violet' },
      ]
    : user.role === 'showroom_manager'
      ? [
          { icon: CalendarCheck, label: 'Booking hôm nay', value: data.bookings_today, note: 'Showroom của bạn', tone: 'blue' },
          { icon: CheckCircle, label: 'Booking sắp tới', value: data.upcoming_bookings, note: `${bookingTotal} booking tổng`, tone: 'green' },
          { icon: CarProfile, label: 'Xe sẵn sàng', value: data.available_vehicle_total, note: `${data.unavailable_vehicle_total || 0} xe không sẵn sàng`, tone: 'orange' },
          { icon: UsersThree, label: 'Nhân viên trực', value: data.staff_on_duty_total, note: `${data.staff_unavailable_total || 0} không khả dụng`, tone: 'violet' },
          { icon: CheckCircle, label: 'Đã hoàn tất', value: data.completed_booking_total, note: 'Trong phạm vi showroom', tone: 'green' },
          { icon: Clock, label: 'No-show', value: data.no_show_booking_total, note: 'Cần theo dõi vận hành', tone: 'orange' },
        ]
      : [
          { icon: Storefront, label: 'Tổng showroom', value: data.showroom_total, note: `${data.active_showroom_total || 0} đang hoạt động`, tone: 'blue' },
          { icon: CalendarCheck, label: 'Tổng booking', value: bookingTotal, note: `${data.bookings_today || 0} booking hôm nay`, tone: 'green' },
          { icon: CarProfile, label: 'Tổng xe demo', value: data.vehicle_total, note: `${data.available_vehicle_total || 0} sẵn sàng · ${data.maintenance_vehicle_total || 0} bảo trì`, tone: 'orange' },
          { icon: UsersThree, label: 'Nhân viên', value: data.staff_total, note: `${data.manager_total || 0} quản lý showroom`, tone: 'violet' },
          { icon: Clock, label: 'Điều chuyển xe', value: data.vehicle_transfer_total, note: 'Lịch sử toàn hệ thống', tone: 'blue' },
          { icon: CheckCircle, label: 'Booking hoàn tất', value: data.completed_booking_total, note: `${data.no_show_booking_total || 0} no-show`, tone: 'green' },
        ]

  return (
    <PageState loading={state.loading} error={state.error}>
      <div className="page-heading">
        <div><h2>Nhịp vận hành hôm nay</h2><p>Dữ liệu được giới hạn tự động theo quyền {user.display_name}.</p></div>
        <button className="secondary-button" onClick={state.reload}>Làm mới dữ liệu</button>
      </div>
      <div className="metric-grid">
        {metrics.map((metric) => <Metric key={metric.label} {...metric} />)}
      </div>
      <div className="dashboard-grid">
        <article className="panel panel--full">
          <div className="panel__header"><div><span className="eyebrow">14 ngày</span><h3>Nhịp lịch lái thử</h3></div><CalendarCheck size={22} /></div>
          <TrendChart points={data.booking_trend || []} />
        </article>
        <article className="panel">
          <div className="panel__header"><div><span className="eyebrow">7 ngày tới</span><h3>Công suất lịch</h3></div><Clock size={22} /></div>
          <CapacityChart points={data.slot_utilization || []} />
        </article>
        <article className="panel">
          <div className="panel__header"><div><span className="eyebrow">Booking pipeline</span><h3>Phân bố trạng thái</h3></div><Clock size={22} /></div>
          <div className="status-bars">
            {Object.entries(data.booking_counts || {}).map(([status, count]) => (
              <div className="status-bar" key={status}>
                <div><span>{statusLabels[status] || status}</span><strong>{count.toLocaleString('vi-VN')}</strong></div>
                <div className="status-bar__track"><span style={{ width: `${Math.max((count / maxBooking) * 100, 3)}%` }} /></div>
              </div>
            ))}
          </div>
        </article>
        <article className="panel panel--full">
          <div className="panel__header"><div><span className="eyebrow">Cập nhật gần nhất</span><h3>Lịch lái thử mới</h3></div><Storefront size={22} /></div>
          <div className="compact-list">
            {(data.recent_bookings || []).map((booking) => (
              <div className="compact-row" key={booking.id}>
                <div className="date-chip"><strong>{new Date(booking.start_at).getDate()}</strong><span>Th {new Date(booking.start_at).getMonth() + 1}</span></div>
                <div className="compact-row__main"><strong>{booking.vehicle_model} · {booking.vehicle_variant}</strong><span>{booking.showroom_name} · {formatDateTime(booking.start_at)}</span></div>
                <div className="compact-row__meta"><StatusBadge status={booking.status} /><small>{booking.booking_code || 'Draft'}</small></div>
              </div>
            ))}
            {!data.recent_bookings?.length && <div className="empty-state">Chưa có booking trong phạm vi này.</div>}
          </div>
        </article>
        {user.role === 'operations_admin' && (
          <article className="panel panel--full">
            <div className="panel__header"><div><span className="eyebrow">Kiểm soát thay đổi</span><h3>Audit gần đây</h3></div><Clock size={22} /></div>
            <div className="compact-list">
              {(data.recent_audit_events || []).map((event) => (
                <div className="compact-row" key={event.id}>
                  <div className="date-chip"><Clock size={19} /></div>
                  <div className="compact-row__main"><strong>{event.action}</strong><span>{event.resource_type}{event.resource_id ? ` · ${event.resource_id}` : ''}</span></div>
                  <div className="compact-row__meta"><strong>{event.actor_name}</strong><small>{formatDateTime(event.created_at)}</small></div>
                </div>
              ))}
              {!data.recent_audit_events?.length && <div className="empty-state">Chưa có audit event.</div>}
            </div>
          </article>
        )}
      </div>
    </PageState>
  )
}
