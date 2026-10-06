import { ArrowsLeftRight, CarProfile, MapPin } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import { api } from '../api.js'
import { PageState } from '../components/PageState.jsx'
import { useRemote } from '../hooks.js'
import { formatDateTime } from '../utils.js'

function initialEffectiveTime() {
  const date = new Date(Date.now() + 5 * 60 * 1000)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

export function TransfersPage({ token }) {
  const [vehicleId, setVehicleId] = useState('')
  const [destinationId, setDestinationId] = useState('')
  const [effectiveAt, setEffectiveAt] = useState(initialEffectiveTime)
  const [message, setMessage] = useState('')
  const [formError, setFormError] = useState('')
  const showrooms = useRemote(() => api.showrooms(token), [token])
  const vehicles = useRemote(() => api.vehicles(token, {}), [token])
  const transfers = useRemote(() => api.vehicleTransfers(token), [token])
  const vehicle = useMemo(() => (vehicles.data || []).find((item) => item.id === vehicleId), [vehicles.data, vehicleId])

  const submit = async (event) => {
    event.preventDefault()
    if (!window.confirm(`Điều chuyển ${vehicle?.asset_code} sang showroom đã chọn?`)) return
    setMessage('')
    setFormError('')
    try {
      await api.transferVehicle(token, vehicleId, {
        to_showroom_id: destinationId,
        effective_at: new Date(effectiveAt).toISOString(),
      })
      setMessage('Điều chuyển thành công. Showroom hiện tại và lịch sử xe đã được cập nhật.')
      setVehicleId('')
      setDestinationId('')
      setEffectiveAt(initialEffectiveTime())
      await Promise.all([vehicles.reload(), transfers.reload()])
    } catch (error) {
      setFormError(error.message)
    }
  }

  return (
    <PageState loading={showrooms.loading || vehicles.loading || transfers.loading} error={showrooms.error || vehicles.error || transfers.error}>
      <div className="page-heading"><div><h2>Điều chuyển xe demo</h2><p>Chỉ Operations Admin có quyền; backend từ chối nếu xe còn hold hoặc booking sắp tới.</p></div></div>
      <div className="transfer-layout">
        <article className="panel form-panel">
          <div className="panel__header"><div><span className="eyebrow">Tạo điều chuyển</span><h3>Chọn xe và showroom đích</h3></div><ArrowsLeftRight size={22} /></div>
          <form onSubmit={submit}>
            <label><span>Xe demo</span><select value={vehicleId} onChange={(event) => { setVehicleId(event.target.value); setDestinationId('') }} required><option value="">Chọn xe</option>{(vehicles.data || []).map((item) => <option key={item.id} value={item.id}>{item.asset_code} · {item.showroom_name}</option>)}</select></label>
            {vehicle && <div className="resource-preview"><CarProfile size={23} /><div><strong>{vehicle.vehicle_model} · {vehicle.vehicle_variant}</strong><span><MapPin size={14} />{vehicle.showroom_name}</span></div></div>}
            <label><span>Showroom đích</span><select value={destinationId} onChange={(event) => setDestinationId(event.target.value)} required disabled={!vehicleId}><option value="">Chọn showroom</option>{(showrooms.data || []).filter((item) => item.is_active && item.id !== vehicle?.showroom_id).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <label><span>Thời điểm hiệu lực</span><input type="datetime-local" value={effectiveAt} onChange={(event) => setEffectiveAt(event.target.value)} required /></label>
            {message && <div className="form-success">{message}</div>}
            {formError && <div className="form-error">{formError}</div>}
            <button className="primary-button primary-button--wide" disabled={!vehicleId || !destinationId}><ArrowsLeftRight size={18} />Xác nhận điều chuyển</button>
          </form>
        </article>
        <article className="panel">
          <div className="panel__header"><div><span className="eyebrow">Lịch sử</span><h3>{transfers.data?.length || 0} lần điều chuyển</h3></div><CarProfile size={22} /></div>
          <div className="transfer-list">{(transfers.data || []).map((item) => <div className="transfer-row" key={item.id}><div><strong>{item.asset_code}</strong><span>{item.from_showroom_name} → {item.to_showroom_name}</span></div><div><span className="presence presence--active">{item.status}</span><small>{formatDateTime(item.effective_at || item.completed_at)}</small></div></div>)}{!transfers.data?.length && <div className="empty-state">Chưa có lịch sử điều chuyển.</div>}</div>
        </article>
      </div>
    </PageState>
  )
}
