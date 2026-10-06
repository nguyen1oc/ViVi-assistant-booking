import { BatteryCharging, CarProfile, Funnel, MapPin, Wrench } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import { api } from '../api.js'
import { PageState } from '../components/PageState.jsx'
import { StatusBadge } from '../components/StatusBadge.jsx'
import { useRemote } from '../hooks.js'

const vehicleStatuses = ['', 'available', 'in_use', 'charging', 'maintenance', 'out_of_service']

export function FleetPage({ token, user }) {
  const [showroomId, setShowroomId] = useState(user.showroom_ids?.[0] || '')
  const [modelId, setModelId] = useState('')
  const [variantId, setVariantId] = useState('')
  const [status, setStatus] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const showrooms = useRemote(() => api.showrooms(token), [token])
  const options = useRemote(() => api.vehicles(token, {}), [token])
  const vehicles = useRemote(
    () => api.vehicles(token, {
      showroom_id: showroomId,
      model_id: modelId,
      variant_id: variantId,
      operational_status: status,
    }),
    [token, showroomId, modelId, variantId, status],
  )
  const models = useMemo(() => [...new Map((options.data || []).map((item) => [item.model_id, { id: item.model_id, name: item.vehicle_model }])).values()], [options.data])
  const variants = useMemo(() => [...new Map((options.data || []).filter((item) => !modelId || item.model_id === modelId).map((item) => [item.variant_id, { id: item.variant_id, name: `${item.vehicle_model} · ${item.vehicle_variant}` }])).values()], [options.data, modelId])

  const updateStatus = async (vehicle, operationalStatus) => {
    if (['maintenance', 'out_of_service'].includes(operationalStatus)
      && !window.confirm(`Xác nhận chuyển ${vehicle.asset_code} sang trạng thái ${operationalStatus}?`)) return
    setMessage('')
    setError('')
    try {
      await api.updateVehicle(token, vehicle.id, { operational_status: operationalStatus })
      setMessage(`Đã cập nhật trạng thái ${vehicle.asset_code}.`)
      await Promise.all([vehicles.reload(), options.reload()])
    } catch (caught) {
      setError(caught.message)
    }
  }

  const clearFilters = () => {
    if (user.role === 'operations_admin') setShowroomId('')
    setModelId('')
    setVariantId('')
    setStatus('')
  }

  return (
    <PageState loading={showrooms.loading || options.loading || vehicles.loading} error={showrooms.error || options.error || vehicles.error}>
      <div className="page-heading"><div><h2>Đội xe demo</h2><p>Quản lý trạng thái vận hành; điều chuyển showroom chỉ có ở tài khoản Operations Admin.</p></div></div>
      <div className="filter-bar">
        <Funnel size={20} />
        {user.role === 'operations_admin' && <select value={showroomId} onChange={(event) => setShowroomId(event.target.value)} aria-label="Lọc xe theo showroom"><option value="">Tất cả showroom</option>{(showrooms.data || []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
        <select value={modelId} onChange={(event) => { setModelId(event.target.value); setVariantId('') }} aria-label="Lọc xe theo model"><option value="">Tất cả model</option>{models.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <select value={variantId} onChange={(event) => setVariantId(event.target.value)} aria-label="Lọc xe theo phiên bản"><option value="">Tất cả phiên bản</option>{variants.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Lọc xe theo trạng thái"><option value="">Tất cả trạng thái</option>{vehicleStatuses.slice(1).map((item) => <option key={item} value={item}>{item}</option>)}</select>
        {(modelId || variantId || status || (showroomId && user.role === 'operations_admin')) && <button className="text-button" onClick={clearFilters}>Xóa bộ lọc</button>}
      </div>
      {message && <div className="form-success banner-message">{message}</div>}{error && <div className="form-error banner-message">{error}</div>}
      <div className="fleet-grid">
        {(vehicles.data || []).map((vehicle) => (
          <article className="vehicle-card" key={vehicle.id}>
            <div className="vehicle-card__top"><div className="vehicle-card__icon"><CarProfile size={28} weight="duotone" /></div><StatusBadge status={vehicle.operational_status} /></div>
            <span className="eyebrow">{vehicle.asset_code}</span><h3>{vehicle.vehicle_model} · {vehicle.vehicle_variant}</h3>
            <div className="vehicle-card__meta"><span><MapPin size={17} />{vehicle.showroom_name}</span><span><BatteryCharging size={17} />{vehicle.battery_soc ?? '—'}% · tối thiểu {vehicle.minimum_booking_soc}%</span><span><Wrench size={17} />{vehicle.plate_number || 'Chưa có biển số'}</span></div>
            <div className="battery"><span style={{ width: `${Math.min(vehicle.battery_soc || 0, 100)}%` }} /></div>
            <label className="inline-field"><span>Trạng thái vận hành</span><select value={vehicle.operational_status} onChange={(event) => updateStatus(vehicle, event.target.value)}><option value="available">Sẵn sàng</option><option value="charging">Đang sạc</option><option value="maintenance">Bảo trì</option><option value="out_of_service">Ngừng phục vụ</option><option value="in_use">Đang sử dụng</option></select></label>
          </article>
        ))}
      </div>
      {!vehicles.data?.length && <div className="empty-state">Không có xe demo phù hợp bộ lọc.</div>}
    </PageState>
  )
}
