import { CalendarPlus, Clock, Plus, UserFocus, WarningCircle } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import { api } from '../api.js'
import { PageState } from '../components/PageState.jsx'
import { useRemote } from '../hooks.js'
import { formatDateTime } from '../utils.js'

function asIso(value) {
  return value ? new Date(value).toISOString() : ''
}

function asInput(value) {
  if (!value) return ''
  const date = new Date(value)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

export function TeamPage({ token, user }) {
  const canManage = user.role !== 'staff'
  const [showroomId, setShowroomId] = useState(user.showroom_ids?.[0] || '')
  const [mode, setMode] = useState('shift')
  const [staffId, setStaffId] = useState('')
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [reason, setReason] = useState('')
  const [editingShift, setEditingShift] = useState(null)
  const [message, setMessage] = useState('')
  const [formError, setFormError] = useState('')
  const showrooms = useRemote(() => api.showrooms(token), [token])
  const staff = useRemote(() => api.staff(token, showroomId), [token, showroomId])
  const shifts = useRemote(() => api.shifts(token, { showroom_id: showroomId }), [token, showroomId])
  const unavailable = useRemote(() => api.unavailability(token, { showroom_id: showroomId }), [token, showroomId])
  const selectedStaff = useMemo(() => staff.data?.find((item) => item.id === staffId), [staff.data, staffId])

  const resetForm = () => {
    setEditingShift(null)
    setStaffId('')
    setStartAt('')
    setEndAt('')
    setReason('')
  }

  const submit = async (event) => {
    event.preventDefault()
    setMessage('')
    setFormError('')
    const body = { staff_id: staffId, showroom_id: showroomId, start_at: asIso(startAt), end_at: asIso(endAt) }
    try {
      if (editingShift) {
        await api.updateShift(token, editingShift.id, { start_at: body.start_at, end_at: body.end_at })
        setMessage('Đã cập nhật ca làm và ghi audit event.')
        await shifts.reload()
      } else if (mode === 'shift') {
        await api.createShift(token, body)
        setMessage(`Đã tạo ca cho ${selectedStaff?.full_name || 'nhân viên'}.`)
        await shifts.reload()
      } else {
        await api.createUnavailability(token, { ...body, reason })
        setMessage('Đã ghi nhận thời gian không khả dụng và hủy ca bị trùng.')
        await Promise.all([shifts.reload(), unavailable.reload()])
      }
      resetForm()
    } catch (error) {
      setFormError(error.message)
    }
  }

  const editShift = (shift) => {
    setMode('shift')
    setEditingShift(shift)
    setStaffId(shift.sales_staff_id)
    setStartAt(asInput(shift.start_at))
    setEndAt(asInput(shift.end_at))
    setMessage('')
    setFormError('')
  }

  const cancelShift = async (shift) => {
    if (!window.confirm(`Hủy ca của ${shift.staff_name}?`)) return
    setMessage('')
    setFormError('')
    try {
      await api.updateShift(token, shift.id, { status: 'cancelled' })
      setMessage('Đã hủy ca làm.')
      await shifts.reload()
    } catch (error) {
      setFormError(error.message)
    }
  }

  return (
    <PageState loading={showrooms.loading || staff.loading || shifts.loading || unavailable.loading} error={showrooms.error || staff.error || shifts.error || unavailable.error}>
      <div className="page-heading">
        <div>
          <h2>{canManage ? 'Nhân sự và lịch làm việc' : 'Lịch làm việc của tôi'}</h2>
          <p>{canManage ? 'Ca làm và thời gian không khả dụng chỉ áp dụng trong showroom được cấp quyền.' : 'Chỉ hiển thị lịch gắn với hồ sơ nhân viên của bạn.'}</p>
        </div>
        {user.role === 'operations_admin' && <select className="heading-select" value={showroomId} onChange={(event) => { setShowroomId(event.target.value); resetForm() }} aria-label="Chọn showroom cần quản lý nhân sự"><option value="">Chọn showroom</option>{(showrooms.data || []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
      </div>
      {message && <div className="form-success banner-message">{message}</div>}
      {formError && <div className="form-error banner-message">{formError}</div>}
      {canManage && (
        <div className="team-grid">
          <article className="panel">
            <div className="panel__header"><div><span className="eyebrow">Đội ngũ</span><h3>{staff.data?.length || 0} nhân viên</h3></div><UserFocus size={22} /></div>
            <div className="people-list">
              {(staff.data || []).map((person) => (
                <div className="person-row" key={person.id}>
                  <div className="avatar avatar--light">{person.full_name.slice(0, 1)}</div>
                  <div><strong>{person.full_name}</strong><span>{person.employee_code} · {person.role}</span></div>
                  <span className={`presence ${person.status === 'active' ? 'presence--active' : ''}`}>{person.status}</span>
                </div>
              ))}
            </div>
          </article>
          <article className="panel form-panel">
            {!editingShift && <div className="segmented"><button className={mode === 'shift' ? 'active' : ''} onClick={() => setMode('shift')}>Tạo ca làm</button><button className={mode === 'unavailable' ? 'active' : ''} onClick={() => setMode('unavailable')}>Không khả dụng</button></div>}
            {editingShift && <div className="panel__header"><div><span className="eyebrow">Chỉnh sửa</span><h3>Ca của {editingShift.staff_name}</h3></div><button className="text-button" onClick={resetForm}>Hủy sửa</button></div>}
            <form onSubmit={submit}>
              <label><span>Nhân viên</span><select value={staffId} onChange={(event) => setStaffId(event.target.value)} required disabled={Boolean(editingShift)}><option value="">Chọn nhân viên</option>{(staff.data || []).map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></label>
              <div className="form-columns"><label><span>Bắt đầu</span><input type="datetime-local" value={startAt} onChange={(event) => setStartAt(event.target.value)} required /></label><label><span>Kết thúc</span><input type="datetime-local" value={endAt} onChange={(event) => setEndAt(event.target.value)} required /></label></div>
              {mode === 'unavailable' && !editingShift && <label><span>Lý do</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Đào tạo, nghỉ phép…" required /></label>}
              <button className="primary-button primary-button--wide"><Plus size={18} />{editingShift ? 'Lưu thay đổi' : mode === 'shift' ? 'Tạo ca làm việc' : 'Thêm thời gian không khả dụng'}</button>
            </form>
          </article>
        </div>
      )}
      <div className="two-column-panels">
        <article className="panel">
          <div className="panel__header"><div><span className="eyebrow">Lịch đã xếp</span><h3>Ca làm việc</h3></div><CalendarPlus size={22} /></div>
          <div className="timeline-list">{(shifts.data || []).slice(0, 30).map((item) => <div className="timeline-row" key={item.id}><div className="timeline-dot" /><div><strong>{item.staff_name}</strong><span>{formatDateTime(item.start_at)} → {formatDateTime(item.end_at)}</span></div><span className={`presence ${item.status === 'scheduled' ? 'presence--active' : ''}`}>{item.status}</span>{canManage && item.status === 'scheduled' && <div className="row-actions"><button className="text-button" onClick={() => editShift(item)}>Sửa</button><button className="text-button text-button--danger" onClick={() => cancelShift(item)}>Hủy</button></div>}</div>)}{!shifts.data?.length && <div className="empty-state"><Clock size={22} />Chưa có ca làm việc.</div>}</div>
        </article>
        <article className="panel">
          <div className="panel__header"><div><span className="eyebrow">Ngoại lệ</span><h3>Không khả dụng</h3></div><WarningCircle size={22} /></div>
          <div className="timeline-list">{(unavailable.data || []).slice(0, 30).map((item) => <div className="timeline-row timeline-row--warning" key={item.id}><div className="timeline-dot" /><div><strong>{item.staff_name}</strong><span>{formatDateTime(item.start_at)} → {formatDateTime(item.end_at)} · {item.reason}</span></div></div>)}{!unavailable.data?.length && <div className="empty-state">Chưa có ngoại lệ lịch.</div>}</div>
        </article>
      </div>
    </PageState>
  )
}
