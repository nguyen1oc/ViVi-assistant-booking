import { CalendarCheck, Clock, Plus, Trash, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { PageState } from '../components/PageState.jsx'
import { useRemote } from '../hooks.js'
import { formatDateTime } from '../utils.js'

const days = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ Nhật']

function asIso(value) {
  return value ? new Date(value).toISOString() : ''
}

export function ShowroomSchedulePage({ token, user }) {
  const [showroomId, setShowroomId] = useState(user.showroom_ids?.[0] || '')
  const [hours, setHours] = useState({})
  const [vehicleId, setVehicleId] = useState('')
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [reason, setReason] = useState('')
  const [message, setMessage] = useState('')
  const [formError, setFormError] = useState('')
  const showrooms = useRemote(() => api.showrooms(token), [token])
  const hoursState = useRemote(() => (showroomId ? api.operatingHours(token, showroomId) : Promise.resolve([])), [token, showroomId])
  const vehicles = useRemote(() => (showroomId ? api.vehicles(token, { showroom_id: showroomId }) : Promise.resolve([])), [token, showroomId])
  const unavailable = useRemote(() => api.vehicleUnavailability(token, { showroom_id: showroomId }), [token, showroomId])

  useEffect(() => {
    const next = {}
    for (let day = 0; day < 7; day += 1) {
      const record = (hoursState.data || []).find((item) => item.day_of_week === day)
      next[day] = {
        open_time: record?.open_time?.slice(0, 5) || '08:00',
        close_time: record?.close_time?.slice(0, 5) || '18:00',
        is_closed: Boolean(record?.is_closed),
      }
    }
    setHours(next)
  }, [hoursState.data, showroomId])

  const changeHour = (day, key, value) => setHours((current) => ({
    ...current,
    [day]: { ...current[day], [key]: value },
  }))

  const saveHour = async (day) => {
    setMessage('')
    setFormError('')
    try {
      await api.updateOperatingHour(token, showroomId, day, { day_of_week: day, ...hours[day] })
      setMessage(`Đã lưu giờ hoạt động ${days[day]}.`)
      await hoursState.reload()
    } catch (error) {
      setFormError(error.message)
    }
  }

  const createBlock = async (event) => {
    event.preventDefault()
    setMessage('')
    setFormError('')
    try {
      await api.createVehicleUnavailability(token, vehicleId, {
        start_at: asIso(startAt),
        end_at: asIso(endAt),
        reason,
      })
      setMessage('Đã khóa xe và chặn các slot trống trong khoảng thời gian này.')
      setVehicleId('')
      setStartAt('')
      setEndAt('')
      setReason('')
      await unavailable.reload()
    } catch (error) {
      setFormError(error.message)
    }
  }

  const removeBlock = async (record) => {
    if (!window.confirm(`Gỡ khoảng khóa của xe ${record.asset_code}?`)) return
    setMessage('')
    setFormError('')
    try {
      await api.removeVehicleUnavailability(token, record.id)
      setMessage('Đã gỡ khoảng khóa xe và mở lại các slot liên quan còn hợp lệ.')
      await unavailable.reload()
    } catch (error) {
      setFormError(error.message)
    }
  }

  return (
    <PageState loading={showrooms.loading || hoursState.loading || vehicles.loading || unavailable.loading} error={showrooms.error || hoursState.error || vehicles.error || unavailable.error}>
      <div className="page-heading">
        <div><h2>Lịch vận hành showroom</h2><p>Giờ mở cửa và các khoảng khóa xe demo đều được kiểm tra theo scope showroom.</p></div>
        {user.role === 'operations_admin' && <select className="heading-select" value={showroomId} onChange={(event) => setShowroomId(event.target.value)} aria-label="Chọn showroom cần quản lý lịch"><option value="">Chọn showroom</option>{(showrooms.data || []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
      </div>
      {message && <div className="form-success banner-message">{message}</div>}
      {formError && <div className="form-error banner-message">{formError}</div>}
      {!showroomId ? <div className="empty-state">Chọn showroom để quản lý lịch.</div> : (
        <div className="schedule-layout">
          <article className="panel">
            <div className="panel__header"><div><span className="eyebrow">Theo tuần</span><h3>Giờ hoạt động</h3></div><Clock size={22} /></div>
            <div className="hours-list">
              {days.map((label, day) => (
                <div className="hours-row" key={label}>
                  <strong>{label}</strong>
                  <input type="time" value={hours[day]?.open_time || ''} disabled={hours[day]?.is_closed} onChange={(event) => changeHour(day, 'open_time', event.target.value)} />
                  <span>đến</span>
                  <input type="time" value={hours[day]?.close_time || ''} disabled={hours[day]?.is_closed} onChange={(event) => changeHour(day, 'close_time', event.target.value)} />
                  <label className="switch-field"><input type="checkbox" checked={hours[day]?.is_closed || false} onChange={(event) => changeHour(day, 'is_closed', event.target.checked)} />Đóng cửa</label>
                  <button className="text-button" onClick={() => saveHour(day)}>Lưu</button>
                </div>
              ))}
            </div>
          </article>
          <article className="panel form-panel">
            <div className="panel__header"><div><span className="eyebrow">Ngoại lệ</span><h3>Khóa xe theo thời gian</h3></div><CalendarCheck size={22} /></div>
            <form onSubmit={createBlock}>
              <label><span>Xe demo</span><select value={vehicleId} onChange={(event) => setVehicleId(event.target.value)} required><option value="">Chọn xe</option>{(vehicles.data || []).map((item) => <option key={item.id} value={item.id}>{item.asset_code} · {item.vehicle_model}</option>)}</select></label>
              <div className="form-columns"><label><span>Bắt đầu</span><input type="datetime-local" value={startAt} onChange={(event) => setStartAt(event.target.value)} required /></label><label><span>Kết thúc</span><input type="datetime-local" value={endAt} onChange={(event) => setEndAt(event.target.value)} required /></label></div>
              <label><span>Lý do</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Bảo trì, sự kiện showroom…" required /></label>
              <button className="primary-button primary-button--wide"><Plus size={18} />Tạo khoảng khóa</button>
            </form>
          </article>
          <article className="panel panel--full">
            <div className="panel__header"><div><span className="eyebrow">Đang áp dụng</span><h3>Khoảng khóa xe</h3></div><WarningCircle size={22} /></div>
            <div className="timeline-list">{(unavailable.data || []).map((item) => <div className="timeline-row timeline-row--warning" key={item.id}><div className="timeline-dot" /><div><strong>{item.asset_code}</strong><span>{formatDateTime(item.start_at)} → {formatDateTime(item.end_at)} · {item.reason}</span></div><button className="icon-button icon-button--danger" onClick={() => removeBlock(item)} title="Gỡ khoảng khóa"><Trash size={17} /></button></div>)}{!unavailable.data?.length && <div className="empty-state">Chưa có khoảng khóa xe nào.</div>}</div>
          </article>
        </div>
      )}
    </PageState>
  )
}
