import { Buildings, Key, Plus, ShieldCheck, UserFocus, UsersThree } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import { api } from '../api.js'
import { PageState } from '../components/PageState.jsx'
import { useRemote } from '../hooks.js'
import { formatDateTime, roleLabels } from '../utils.js'

const emptyForm = {
  username: '',
  displayName: '',
  password: '',
  confirmation: '',
  role: 'staff',
  showroomId: '',
  showroomIds: [],
  staffId: '',
}

export function UsersPage({ token }) {
  const [roleFilter, setRoleFilter] = useState('')
  const [showroomFilter, setShowroomFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [form, setForm] = useState(emptyForm)
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [formError, setFormError] = useState('')
  const [editForm, setEditForm] = useState(null)
  const [editMessage, setEditMessage] = useState('')
  const [editError, setEditError] = useState('')
  const [editSubmitting, setEditSubmitting] = useState(false)
  const state = useRemote(async () => {
    const [users, allUsers, showrooms, staff] = await Promise.all([
      api.users(token, {
        role: roleFilter,
        showroom_id: showroomFilter,
        is_active: activeFilter === '' ? '' : activeFilter === 'active',
      }),
      api.users(token),
      api.showrooms(token),
      api.staff(token, ''),
    ])
    return { users, allUsers, showrooms, staff }
  }, [token, roleFilter, showroomFilter, activeFilter])

  const showroomsById = useMemo(
    () => Object.fromEntries((state.data?.showrooms || []).map((item) => [item.id, item.name])),
    [state.data?.showrooms],
  )
  const availableStaff = useMemo(() => {
    const linkedStaff = new Set((state.data?.allUsers || []).map((item) => item.staff_id))
    return (state.data?.staff || []).filter(
      (item) => item.showroom_id === form.showroomId && !linkedStaff.has(item.id),
    )
  }, [state.data?.staff, state.data?.allUsers, form.showroomId])

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }))

  const changeRole = (role) => {
    setForm((current) => ({ ...current, role, showroomId: '', showroomIds: [], staffId: '' }))
    setMessage('')
    setFormError('')
  }

  const changeStaff = (staffId) => {
    const selected = availableStaff.find((item) => item.id === staffId)
    setForm((current) => ({
      ...current,
      staffId,
      displayName: current.displayName || selected?.full_name || '',
    }))
  }

  const submit = async (event) => {
    event.preventDefault()
    setMessage('')
    setFormError('')
    if (form.password.length < 8) {
      setFormError('Mật khẩu phải có ít nhất 8 ký tự.')
      return
    }
    if (form.password !== form.confirmation) {
      setFormError('Mật khẩu xác nhận không khớp.')
      return
    }
    if (form.role === 'showroom_manager' && form.showroomIds.length !== 1) {
      setFormError('Quản lý phải được cấp đúng một showroom.')
      return
    }
    setSubmitting(true)
    try {
      const created = await api.createUser(token, {
        username: form.username,
        display_name: form.displayName,
        password: form.password,
        role: form.role,
        staff_id: form.role === 'staff' ? form.staffId : null,
        showroom_ids: form.role === 'showroom_manager' ? form.showroomIds : [],
      })
      setForm(emptyForm)
      setMessage(`Đã tạo tài khoản ${created.username}.`)
      await state.reload()
    } catch (error) {
      setFormError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const beginEdit = (account) => {
    setEditForm({
      id: account.id,
      username: account.username,
      displayName: account.display_name,
      role: account.role,
      showroomId: account.showroom_ids?.[0] || '',
      showroomIds: account.showroom_ids || [],
      staffId: account.staff_id || '',
      isActive: account.is_active,
      password: '',
      confirmation: '',
    })
    setEditMessage('')
    setEditError('')
  }

  const editStaff = useMemo(() => {
    if (!editForm) return []
    const linkedStaff = new Set(
      (state.data?.allUsers || [])
        .filter((item) => item.id !== editForm.id)
        .map((item) => item.staff_id),
    )
    return (state.data?.staff || []).filter(
      (item) => item.showroom_id === editForm.showroomId && !linkedStaff.has(item.id),
    )
  }, [editForm, state.data?.staff, state.data?.allUsers])

  const saveEdit = async (event) => {
    event.preventDefault()
    setEditMessage('')
    setEditError('')
    if (editForm.role === 'showroom_manager' && editForm.showroomIds.length !== 1) {
      setEditError('Quản lý phải được cấp đúng một showroom.')
      return
    }
    if (editForm.role === 'staff' && !editForm.staffId) {
      setEditError('Staff phải được liên kết với một nhân viên.')
      return
    }
    setEditSubmitting(true)
    try {
      await api.updateUser(token, editForm.id, {
        display_name: editForm.displayName,
        role: editForm.role,
        staff_id: editForm.role === 'staff' ? editForm.staffId : null,
        showroom_ids: editForm.role === 'showroom_manager' ? editForm.showroomIds : [],
        is_active: editForm.isActive,
      })
      setEditMessage('Đã cập nhật quyền và thu hồi các phiên cũ nếu phạm vi thay đổi.')
      await state.reload()
    } catch (error) {
      setEditError(error.message)
    } finally {
      setEditSubmitting(false)
    }
  }

  const resetPassword = async () => {
    setEditMessage('')
    setEditError('')
    if (editForm.password.length < 8) {
      setEditError('Mật khẩu mới phải có ít nhất 8 ký tự.')
      return
    }
    if (editForm.password !== editForm.confirmation) {
      setEditError('Mật khẩu xác nhận không khớp.')
      return
    }
    setEditSubmitting(true)
    try {
      await api.resetUserPassword(token, editForm.id, editForm.password)
      setEditForm((current) => ({ ...current, password: '', confirmation: '' }))
      setEditMessage('Đã đặt lại mật khẩu và thu hồi toàn bộ phiên đăng nhập của tài khoản.')
    } catch (error) {
      setEditError(error.message)
    } finally {
      setEditSubmitting(false)
    }
  }

  const revokeSessions = async () => {
    setEditMessage('')
    setEditError('')
    setEditSubmitting(true)
    try {
      const result = await api.revokeUserSessions(token, editForm.id)
      setEditMessage(`Đã thu hồi ${result.sessions_revoked} phiên đăng nhập.`)
    } catch (error) {
      setEditError(error.message)
    } finally {
      setEditSubmitting(false)
    }
  }

  return (
    <PageState loading={state.loading} error={state.error}>
      <div className="page-heading">
        <div>
          <h2>Quản lý tài khoản nội bộ</h2>
          <p>Tạo tài khoản theo đúng vai trò và phạm vi showroom. Mật khẩu không được hiển thị lại sau khi tạo.</p>
        </div>
      </div>
      <div className="account-grid">
        <article className="panel form-panel account-form-panel">
          <div className="panel__header">
            <div><span className="eyebrow">Cấp quyền truy cập</span><h3>Tạo tài khoản mới</h3></div>
            <ShieldCheck size={23} />
          </div>
          <form onSubmit={submit}>
            <label>
              <span>Vai trò</span>
              <select value={form.role} onChange={(event) => changeRole(event.target.value)}>
                <option value="staff">Nhân viên tư vấn</option>
                <option value="showroom_manager">Quản lý showroom</option>
                <option value="operations_admin">Operations Admin</option>
              </select>
            </label>
            {form.role === 'staff' && (
              <label>
                <span>Showroom của nhân viên</span>
                <select value={form.showroomId} onChange={(event) => setForm((current) => ({ ...current, showroomId: event.target.value, staffId: '' }))} required>
                  <option value="">Chọn showroom</option>
                  {(state.data?.showrooms || []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
            )}
            {form.role === 'showroom_manager' && (
              <label>
                <span>Showroom được quản lý</span>
                <select value={form.showroomIds[0] || ''} onChange={(event) => setForm((current) => ({ ...current, showroomIds: event.target.value ? [event.target.value] : [] }))} required>
                  <option value="">Chọn showroom</option>
                  {(state.data?.showrooms || []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
            )}
            {form.role === 'staff' && (
              <label>
                <span>Nhân viên liên kết</span>
                <select value={form.staffId} onChange={(event) => changeStaff(event.target.value)} required disabled={!form.showroomId}>
                  <option value="">{form.showroomId ? 'Chọn nhân viên chưa có tài khoản' : 'Chọn showroom trước'}</option>
                  {availableStaff.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.employee_code}</option>)}
                </select>
              </label>
            )}
            <div className="form-columns">
              <label><span>Tên đăng nhập</span><input value={form.username} onChange={(event) => update('username', event.target.value)} minLength={3} maxLength={80} autoComplete="off" placeholder="staff.hanoi01" required /></label>
              <label><span>Tên hiển thị</span><input value={form.displayName} onChange={(event) => update('displayName', event.target.value)} maxLength={120} placeholder="Nguyễn Văn A" required /></label>
            </div>
            <div className="form-columns">
              <label><span>Mật khẩu</span><input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} minLength={8} maxLength={256} autoComplete="new-password" placeholder="Tối thiểu 8 ký tự" required /></label>
              <label><span>Xác nhận mật khẩu</span><input type="password" value={form.confirmation} onChange={(event) => update('confirmation', event.target.value)} minLength={8} maxLength={256} autoComplete="new-password" placeholder="Nhập lại mật khẩu" required /></label>
            </div>
            <p className="password-hint">Tối thiểu 8 ký tự. Hãy bàn giao mật khẩu cho đúng người dùng qua kênh an toàn.</p>
            {message && <div className="form-success">{message}</div>}
            {formError && <div className="form-error">{formError}</div>}
            <button className="primary-button primary-button--wide" disabled={submitting}>
              <Plus size={18} />{submitting ? 'Đang tạo…' : 'Tạo tài khoản'}
            </button>
          </form>
        </article>

        <article className="panel account-list-panel">
          <div className="panel__header">
            <div><span className="eyebrow">Người dùng hệ thống</span><h3>{state.data?.users.length || 0} tài khoản</h3></div>
            <UsersThree size={23} />
          </div>
          <div className="account-list">
            {(state.data?.users || []).map((account) => (
              <div className="account-row" key={account.id}>
                <div className="account-row__icon">{account.role === 'operations_admin' ? <ShieldCheck size={19} /> : account.role === 'showroom_manager' ? <Buildings size={19} /> : <UserFocus size={19} />}</div>
                <div className="account-row__identity">
                  <strong>{account.display_name}</strong>
                  <span>@{account.username}{account.staff_name ? ` · ${account.staff_name}` : ''}</span>
                </div>
                <div className="account-row__scope">
                  <strong>{roleLabels[account.role]}</strong>
                  <span>{account.showroom_ids.map((id) => showroomsById[id] || id).join(', ') || 'Toàn hệ thống'}</span>
                </div>
                <div className="account-row__status">
                  <span className={`presence ${account.is_active && account.staff_is_active !== false ? 'presence--active' : ''}`}>{!account.is_active ? 'Đã khóa' : account.staff_is_active === false ? 'Nhân sự ngừng hoạt động' : 'Hoạt động'}</span>
                  <small>{account.last_login_at ? `Đăng nhập ${formatDateTime(account.last_login_at)}` : 'Chưa đăng nhập'}</small>
                  <button className="text-button" type="button" onClick={() => beginEdit(account)}>Quản lý</button>
                </div>
              </div>
            ))}
            {!state.data?.users.length && <div className="empty-state">Chưa có tài khoản nội bộ.</div>}
          </div>
        </article>
      </div>
      <div className="filter-bar">
        <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} aria-label="Lọc tài khoản theo vai trò"><option value="">Tất cả vai trò</option><option value="staff">Staff</option><option value="showroom_manager">Showroom Manager</option><option value="operations_admin">Operations Admin</option></select>
        <select value={showroomFilter} onChange={(event) => setShowroomFilter(event.target.value)} aria-label="Lọc tài khoản theo showroom"><option value="">Tất cả showroom</option>{(state.data?.showrooms || []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <select value={activeFilter} onChange={(event) => setActiveFilter(event.target.value)} aria-label="Lọc tài khoản theo trạng thái"><option value="">Tất cả trạng thái</option><option value="active">Đang hoạt động</option><option value="inactive">Đã khóa</option></select>
        {(roleFilter || showroomFilter || activeFilter) && <button className="text-button" onClick={() => { setRoleFilter(''); setShowroomFilter(''); setActiveFilter('') }}>Xóa bộ lọc</button>}
      </div>
      {editForm && (
        <article className="panel account-editor">
          <div className="panel__header">
            <div><span className="eyebrow">Chỉnh quyền tài khoản</span><h3>@{editForm.username}</h3></div>
            <button className="text-button" type="button" onClick={() => setEditForm(null)}>Đóng</button>
          </div>
          <form onSubmit={saveEdit}>
            <div className="form-columns">
              <label><span>Tên hiển thị</span><input value={editForm.displayName} onChange={(event) => setEditForm((current) => ({ ...current, displayName: event.target.value }))} required /></label>
              <label><span>Vai trò</span><select value={editForm.role} onChange={(event) => setEditForm((current) => ({ ...current, role: event.target.value, showroomId: '', showroomIds: [], staffId: '' }))}><option value="staff">Nhân viên tư vấn</option><option value="showroom_manager">Quản lý showroom</option><option value="operations_admin">Operations Admin</option></select></label>
            </div>
            {editForm.role === 'staff' && (
              <div className="form-columns">
                <label><span>Showroom của nhân viên</span><select value={editForm.showroomId} onChange={(event) => setEditForm((current) => ({ ...current, showroomId: event.target.value, staffId: '' }))} required><option value="">Chọn showroom</option>{(state.data?.showrooms || []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
                <label><span>Nhân viên liên kết</span><select value={editForm.staffId} onChange={(event) => setEditForm((current) => ({ ...current, staffId: event.target.value }))} required disabled={!editForm.showroomId}><option value="">Chọn nhân viên</option>{editStaff.map((item) => <option key={item.id} value={item.id}>{item.full_name} · {item.employee_code}</option>)}</select></label>
              </div>
            )}
            {editForm.role === 'showroom_manager' && (
              <label>
                <span>Showroom được quản lý</span>
                <select value={editForm.showroomIds[0] || ''} onChange={(event) => setEditForm((current) => ({ ...current, showroomIds: event.target.value ? [event.target.value] : [] }))} required>
                  <option value="">Chọn showroom</option>
                  {(state.data?.showrooms || []).filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </label>
            )}
            <label className="switch-field"><input type="checkbox" checked={editForm.isActive} onChange={(event) => setEditForm((current) => ({ ...current, isActive: event.target.checked }))} /><span>Cho phép tài khoản đăng nhập</span></label>
            {editMessage && <div className="form-success">{editMessage}</div>}
            {editError && <div className="form-error">{editError}</div>}
            <div className="account-actions"><button className="primary-button" disabled={editSubmitting}>Lưu quyền</button><button className="secondary-button" type="button" disabled={editSubmitting} onClick={revokeSessions}>Thu hồi mọi phiên</button></div>
          </form>
          <div className="password-reset-panel">
            <div><Key size={21} /><div><strong>Đặt lại mật khẩu</strong><span>Thao tác này tự động đăng xuất tài khoản khỏi mọi thiết bị.</span></div></div>
            <div className="form-columns"><label><span>Mật khẩu mới</span><input type="password" value={editForm.password} onChange={(event) => setEditForm((current) => ({ ...current, password: event.target.value }))} minLength={8} autoComplete="new-password" /></label><label><span>Xác nhận</span><input type="password" value={editForm.confirmation} onChange={(event) => setEditForm((current) => ({ ...current, confirmation: event.target.value }))} minLength={8} autoComplete="new-password" /></label></div>
            <button className="secondary-button" type="button" disabled={editSubmitting || !editForm.password} onClick={resetPassword}>Đặt lại mật khẩu</button>
          </div>
        </article>
      )}
    </PageState>
  )
}
