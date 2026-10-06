import {
  ArrowsLeftRight,
  BookOpenText,
  Buildings,
  CalendarCheck,
  CarProfile,
  ChartDonut,
  ClockCounterClockwise,
  List,
  SignOut,
  UsersThree,
  X,
} from '@phosphor-icons/react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useDialogFocus } from '../hooks.js'
import { roleLabels } from '../utils.js'
import vinfastLogo from '../media/vinfast-logo.webp'
import { NotificationCenter } from './NotificationCenter.jsx'

const allNav = [
  { id: 'dashboard', label: 'Tổng quan', icon: ChartDonut, roles: ['staff', 'showroom_manager', 'operations_admin'] },
  { id: 'bookings', label: 'Booking của tôi', icon: CalendarCheck, roles: ['staff'] },
  { id: 'bookings', label: 'Bookings', icon: CalendarCheck, roles: ['showroom_manager', 'operations_admin'] },
  { id: 'team', label: 'Lịch của tôi', icon: UsersThree, roles: ['staff'] },
  { id: 'team', label: 'Nhân sự & ca làm', icon: UsersThree, roles: ['showroom_manager', 'operations_admin'] },
  { id: 'fleet', label: 'Xe demo', icon: CarProfile, roles: ['showroom_manager', 'operations_admin'] },
  { id: 'schedule', label: 'Lịch showroom', icon: CalendarCheck, roles: ['showroom_manager', 'operations_admin'] },
  { id: 'network', label: 'Showrooms', icon: Buildings, roles: ['operations_admin'] },
  { id: 'catalog', label: 'Danh mục xe', icon: BookOpenText, roles: ['operations_admin'] },
  { id: 'transfers', label: 'Điều chuyển xe', icon: ArrowsLeftRight, roles: ['operations_admin'] },
  { id: 'users', label: 'Tài khoản nội bộ', icon: UsersThree, roles: ['operations_admin'] },
  { id: 'audit', label: 'Nhật ký vận hành', icon: ClockCounterClockwise, roles: ['showroom_manager', 'operations_admin'] },
]

export function Shell({ token, user, page, onNavigate, onLogout, children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const sidebarRef = useDialogFocus({ active: mobileOpen, onClose: () => setMobileOpen(false) })
  const contentRef = useRef(null)
  const nav = useMemo(() => allNav.filter((item) => item.roles.includes(user.role)), [user.role])
  const active = nav.find((item) => item.id === page) || nav[0]
  const today = new Intl.DateTimeFormat('vi-VN', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  }).format(new Date())

  const navigate = (id) => {
    onNavigate(id)
    setMobileOpen(false)
  }

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => contentRef.current?.focus({ preventScroll: true }))
    return () => window.cancelAnimationFrame(frame)
  }, [page])

  return (
    <div className="app-shell">
      <aside ref={sidebarRef} className={`sidebar ${mobileOpen ? 'sidebar--open' : ''}`} role={mobileOpen ? 'dialog' : undefined} aria-modal={mobileOpen ? 'true' : undefined} aria-label={mobileOpen ? 'Điều hướng portal' : undefined} tabIndex={mobileOpen ? -1 : undefined}>
        <div className="brand">
          <img className="brand__logo" src={vinfastLogo} alt="VinFast" />
          <div>
            <strong>DriveOps</strong>
            <span>Internal Portal</span>
          </div>
          <button className="icon-button sidebar__close" onClick={() => setMobileOpen(false)} aria-label="Đóng menu">
            <X size={20} />
          </button>
        </div>
        <div className="sidebar__label">Không gian làm việc</div>
        <nav className="nav-list">
          {nav.map(({ id, label, icon: Icon }) => (
            <button key={id} className={page === id ? 'nav-item nav-item--active' : 'nav-item'} onClick={() => navigate(id)} aria-current={page === id ? 'page' : undefined}>
              <Icon size={21} weight={page === id ? 'fill' : 'regular'} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar__footer">
          <div className="user-card">
            <div className="avatar">{user.display_name.slice(0, 1).toUpperCase()}</div>
            <div className="user-card__copy">
              <strong>{user.display_name}</strong>
              <span>{roleLabels[user.role]}</span>
            </div>
            <button className="icon-button icon-button--dark" onClick={onLogout} title="Đăng xuất" aria-label="Đăng xuất">
              <SignOut size={20} />
            </button>
          </div>
        </div>
      </aside>
      {mobileOpen && <button className="sidebar-backdrop" onClick={() => setMobileOpen(false)} aria-label="Đóng menu" />}
      <main className="main-area">
        <header className="topbar">
          <div className="topbar__left">
            <button className="icon-button menu-button" onClick={() => setMobileOpen(true)} aria-label="Mở menu">
              <List size={22} />
            </button>
            <div>
              <span className="eyebrow">{roleLabels[user.role]}</span>
              <h1>{active.label}</h1>
            </div>
          </div>
          <div className="topbar__right">
            <div className="topbar__date">{today}</div>
            <NotificationCenter token={token} onNavigate={navigate} />
          </div>
        </header>
        <section ref={contentRef} id="portal-content" className="page-content" tabIndex={-1}>{children}</section>
      </main>
    </div>
  )
}
