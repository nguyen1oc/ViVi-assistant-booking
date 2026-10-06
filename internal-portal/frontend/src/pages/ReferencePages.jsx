import { BookOpenText, Buildings, ClockCounterClockwise, MapPin, Phone, Plus } from '@phosphor-icons/react'
import { useState } from 'react'
import { api } from '../api.js'
import { PageState } from '../components/PageState.jsx'
import { useRemote } from '../hooks.js'
import { formatDateTime } from '../utils.js'

const emptyShowroom = {
  code: '', name: '', address: '', latitude: '', longitude: '', phone: '', email: '', timezone: 'Asia/Ho_Chi_Minh',
}

export function NetworkPage({ token }) {
  const state = useRemote(() => api.showrooms(token), [token])
  const [form, setForm] = useState(emptyShowroom)
  const [editingId, setEditingId] = useState('')
  const [message, setMessage] = useState('')
  const [formError, setFormError] = useState('')
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  const edit = (showroom) => {
    setEditingId(showroom.id)
    setForm({
      code: showroom.code,
      name: showroom.name,
      address: showroom.address,
      latitude: showroom.latitude,
      longitude: showroom.longitude,
      phone: showroom.phone || '',
      email: showroom.email || '',
      timezone: showroom.timezone || 'Asia/Ho_Chi_Minh',
    })
    setMessage('')
    setFormError('')
  }

  const reset = () => { setEditingId(''); setForm(emptyShowroom) }

  const submit = async (event) => {
    event.preventDefault()
    setMessage('')
    setFormError('')
    const body = { ...form, latitude: Number(form.latitude), longitude: Number(form.longitude) }
    try {
      if (editingId) {
        const { code, ...changes } = body
        void code
        await api.updateShowroom(token, editingId, changes)
        setMessage('Đã cập nhật showroom.')
      } else {
        await api.createShowroom(token, body)
        setMessage('Đã tạo showroom mới.')
      }
      reset()
      await state.reload()
    } catch (error) {
      setFormError(error.message)
    }
  }

  const toggle = async (showroom) => {
    const action = showroom.is_active ? 'ngừng hoạt động' : 'kích hoạt lại'
    if (!window.confirm(`Xác nhận ${action} ${showroom.name}?`)) return
    setMessage('')
    setFormError('')
    try {
      await api.updateShowroom(token, showroom.id, { is_active: !showroom.is_active })
      setMessage(`Đã ${action} showroom.`)
      await state.reload()
    } catch (error) {
      setFormError(error.message)
    }
  }

  return (
    <PageState loading={state.loading} error={state.error}>
      <div className="page-heading"><div><h2>Quản lý showroom</h2><p>{state.data?.length || 0} showroom toàn hệ thống, bao gồm các điểm đã ngừng hoạt động.</p></div></div>
      {message && <div className="form-success banner-message">{message}</div>}
      {formError && <div className="form-error banner-message">{formError}</div>}
      <div className="resource-management-layout">
        <article className="panel form-panel">
          <div className="panel__header"><div><span className="eyebrow">{editingId ? 'Chỉnh sửa' : 'Tạo mới'}</span><h3>{editingId ? form.name : 'Thông tin showroom'}</h3></div><Buildings size={22} /></div>
          <form onSubmit={submit}>
            <div className="form-columns"><label><span>Mã showroom</span><input value={form.code} onChange={(event) => update('code', event.target.value)} disabled={Boolean(editingId)} required /></label><label><span>Tên showroom</span><input value={form.name} onChange={(event) => update('name', event.target.value)} required /></label></div>
            <label><span>Địa chỉ</span><input value={form.address} onChange={(event) => update('address', event.target.value)} required /></label>
            <div className="form-columns"><label><span>Vĩ độ</span><input type="number" step="any" value={form.latitude} onChange={(event) => update('latitude', event.target.value)} required /></label><label><span>Kinh độ</span><input type="number" step="any" value={form.longitude} onChange={(event) => update('longitude', event.target.value)} required /></label></div>
            <div className="form-columns"><label><span>Điện thoại</span><input value={form.phone} onChange={(event) => update('phone', event.target.value)} /></label><label><span>Email</span><input type="email" value={form.email} onChange={(event) => update('email', event.target.value)} /></label></div>
            <div className="account-actions"><button className="primary-button"><Plus size={18} />{editingId ? 'Lưu showroom' : 'Tạo showroom'}</button>{editingId && <button type="button" className="secondary-button" onClick={reset}>Hủy sửa</button>}</div>
          </form>
        </article>
        <div className="showroom-grid showroom-grid--stack">{(state.data || []).map((showroom) => <article className="showroom-card" key={showroom.id}><div className="showroom-card__mark"><Buildings size={25} weight="duotone" /></div><span className="eyebrow">{showroom.code}</span><h3>{showroom.name}</h3><p><MapPin size={17} />{showroom.address}</p><p><Phone size={17} />{showroom.phone || 'Chưa cập nhật'}</p><div className="showroom-card__foot"><span>{showroom.timezone}</span><span className={`presence ${showroom.is_active ? 'presence--active' : ''}`}>{showroom.is_active ? 'Hoạt động' : 'Đã khóa'}</span></div><div className="card-actions"><button className="text-button" onClick={() => edit(showroom)}>Chỉnh sửa</button><button className={`text-button ${showroom.is_active ? 'text-button--danger' : ''}`} onClick={() => toggle(showroom)}>{showroom.is_active ? 'Ngừng hoạt động' : 'Kích hoạt'}</button></div></article>)}</div>
      </div>
    </PageState>
  )
}

const emptyModel = { code: '', name: '', vehicle_type: 'SUV', required_license_class: 'B1', seat_count: '' }
const emptyVariant = { model_id: '', code: '', name: '', battery_capacity_kwh: '', estimated_range_km: '', motor_power_kw: '', default_test_drive_minutes: 30 }

export function CatalogPage({ token }) {
  const state = useRemote(() => api.catalog(token), [token])
  const [mode, setMode] = useState('model')
  const [modelForm, setModelForm] = useState(emptyModel)
  const [variantForm, setVariantForm] = useState(emptyVariant)
  const [message, setMessage] = useState('')
  const [formError, setFormError] = useState('')
  const models = (state.data || []).reduce((result, row) => {
    const model = result[row.model_id] || { ...row, variants: [] }
    if (row.variant_id) model.variants.push(row)
    result[row.model_id] = model
    return result
  }, {})

  const submit = async (event) => {
    event.preventDefault()
    setMessage('')
    setFormError('')
    try {
      if (mode === 'model') {
        await api.createVehicleModel(token, {
          ...modelForm,
          seat_count: modelForm.seat_count ? Number(modelForm.seat_count) : null,
        })
        setModelForm(emptyModel)
        setMessage('Đã tạo model mới.')
      } else {
        await api.createVehicleVariant(token, {
          ...variantForm,
          battery_capacity_kwh: variantForm.battery_capacity_kwh ? Number(variantForm.battery_capacity_kwh) : null,
          estimated_range_km: variantForm.estimated_range_km ? Number(variantForm.estimated_range_km) : null,
          motor_power_kw: variantForm.motor_power_kw ? Number(variantForm.motor_power_kw) : null,
          default_test_drive_minutes: Number(variantForm.default_test_drive_minutes),
        })
        setVariantForm(emptyVariant)
        setMessage('Đã tạo phiên bản xe mới.')
      }
      await state.reload()
    } catch (error) {
      setFormError(error.message)
    }
  }

  const toggleModel = async (model) => {
    try {
      await api.updateVehicleModel(token, model.model_id, { is_active: !model.model_active })
      await state.reload()
    } catch (error) { setFormError(error.message) }
  }

  const toggleVariant = async (variant) => {
    try {
      await api.updateVehicleVariant(token, variant.variant_id, { is_active: !variant.variant_active })
      await state.reload()
    } catch (error) { setFormError(error.message) }
  }

  return (
    <PageState loading={state.loading} error={state.error}>
      <div className="page-heading"><div><h2>Danh mục xe</h2><p>Operations Admin quản lý model/variant master; hệ thống không hard-delete dữ liệu đang được tham chiếu.</p></div></div>
      {message && <div className="form-success banner-message">{message}</div>}{formError && <div className="form-error banner-message">{formError}</div>}
      <article className="panel form-panel catalog-form">
        <div className="segmented"><button className={mode === 'model' ? 'active' : ''} onClick={() => setMode('model')}>Tạo model</button><button className={mode === 'variant' ? 'active' : ''} onClick={() => setMode('variant')}>Tạo phiên bản</button></div>
        <form onSubmit={submit}>
          {mode === 'model' ? <><div className="form-columns"><label><span>Mã model</span><input value={modelForm.code} onChange={(event) => setModelForm({ ...modelForm, code: event.target.value })} required /></label><label><span>Tên model</span><input value={modelForm.name} onChange={(event) => setModelForm({ ...modelForm, name: event.target.value })} required /></label></div><div className="form-columns"><label><span>Loại xe</span><input value={modelForm.vehicle_type} onChange={(event) => setModelForm({ ...modelForm, vehicle_type: event.target.value })} required /></label><label><span>Hạng GPLX</span><input value={modelForm.required_license_class} onChange={(event) => setModelForm({ ...modelForm, required_license_class: event.target.value })} /></label></div></> : <><label><span>Model</span><select value={variantForm.model_id} onChange={(event) => setVariantForm({ ...variantForm, model_id: event.target.value })} required><option value="">Chọn model</option>{Object.values(models).map((item) => <option key={item.model_id} value={item.model_id}>{item.model_name}</option>)}</select></label><div className="form-columns"><label><span>Mã phiên bản</span><input value={variantForm.code} onChange={(event) => setVariantForm({ ...variantForm, code: event.target.value })} required /></label><label><span>Tên phiên bản</span><input value={variantForm.name} onChange={(event) => setVariantForm({ ...variantForm, name: event.target.value })} required /></label></div><div className="form-columns"><label><span>Pin (kWh)</span><input type="number" step="any" value={variantForm.battery_capacity_kwh} onChange={(event) => setVariantForm({ ...variantForm, battery_capacity_kwh: event.target.value })} /></label><label><span>Tầm hoạt động (km)</span><input type="number" step="any" value={variantForm.estimated_range_km} onChange={(event) => setVariantForm({ ...variantForm, estimated_range_km: event.target.value })} /></label></div></>}
          <button className="primary-button"><Plus size={18} />Tạo {mode === 'model' ? 'model' : 'phiên bản'}</button>
        </form>
      </article>
      <div className="catalog-grid">{Object.values(models).map((model) => <article className="catalog-card" key={model.model_id}><div className="catalog-card__header"><div className="catalog-card__mark"><BookOpenText size={24} /></div><div><span className="eyebrow">{model.model_code}</span><h3>{model.model_name}</h3></div><span className={`presence ${model.model_active ? 'presence--active' : ''}`}>{model.model_active ? 'Active' : 'Inactive'}</span></div><button className="text-button catalog-toggle" onClick={() => toggleModel(model)}>{model.model_active ? 'Ngừng model' : 'Kích hoạt model'}</button><div className="variant-list">{model.variants.map((variant) => <div key={variant.variant_id}><strong>{variant.variant_name}</strong><span>{variant.battery_capacity_kwh || '—'} kWh</span><span>{variant.estimated_range_km || '—'} km</span><button className="text-button" onClick={() => toggleVariant(variant)}>{variant.variant_active ? 'Tắt' : 'Bật'}</button></div>)}</div></article>)}</div>
    </PageState>
  )
}

export function AuditPage({ token }) {
  const state = useRemote(() => api.audit(token), [token])
  return (
    <PageState loading={state.loading} error={state.error}>
      <div className="page-heading"><div><h2>Nhật ký vận hành</h2><p>Các thay đổi nội bộ quan trọng được lưu cùng actor và phạm vi showroom.</p></div><button className="secondary-button" onClick={state.reload}>Làm mới</button></div>
      <article className="panel"><div className="audit-list">{(state.data || []).map((event) => <div className="audit-row" key={event.id}><div className="audit-row__icon"><ClockCounterClockwise size={20} /></div><div><strong>{event.action}</strong><span>{event.resource_type}{event.resource_id ? ` · ${event.resource_id}` : ''}</span></div><div><strong>{event.actor_name}</strong><span>{formatDateTime(event.created_at)}</span></div></div>)}{!state.data?.length && <div className="empty-state">Chưa có thay đổi nội bộ nào được ghi nhận.</div>}</div></article>
    </PageState>
  )
}
