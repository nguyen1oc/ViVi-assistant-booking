import { Bell, CalendarCheck, Check, SpinnerGap } from '@phosphor-icons/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { formatDateTime } from '../utils.js'

const POLL_INTERVAL_MS = 10_000

export function NotificationCenter({ token, onNavigate }) {
  const [items, setItems] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const rootRef = useRef(null)
  const triggerRef = useRef(null)
  const panelRef = useRef(null)

  const loadNotifications = useCallback(async ({ silent = false } = {}) => {
    if (!silent) setLoading(true)
    try {
      const result = await api.notifications(token, { limit: 30 })
      setItems(result.items)
      setUnreadCount(result.unread_count)
      setError('')
    } catch (requestError) {
      if (!silent) setError(requestError.message)
    } finally {
      if (!silent) setLoading(false)
    }
  }, [token])

  useEffect(() => {
    loadNotifications()
    const poll = window.setInterval(() => loadNotifications({ silent: true }), POLL_INTERVAL_MS)
    const refreshOnFocus = () => loadNotifications({ silent: true })
    window.addEventListener('focus', refreshOnFocus)
    return () => {
      window.clearInterval(poll)
      window.removeEventListener('focus', refreshOnFocus)
    }
  }, [loadNotifications])

  useEffect(() => {
    if (!open) return undefined
    const closeOnOutsideClick = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }
    const closeOnEscape = (event) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      setOpen(false)
      triggerRef.current?.focus({ preventScroll: true })
    }
    const focusFrame = window.requestAnimationFrame(() => {
      const firstAction = panelRef.current?.querySelector('button:not([disabled])')
      ;(firstAction || panelRef.current)?.focus({ preventScroll: true })
    })
    document.addEventListener('pointerdown', closeOnOutsideClick)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      window.cancelAnimationFrame(focusFrame)
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [open])

  const openPanel = () => {
    setOpen((current) => !current)
    if (!open) loadNotifications({ silent: true })
  }

  const openNotification = async (notification) => {
    if (!notification.read_at) {
      try {
        const result = await api.markNotificationRead(token, notification.id)
        setItems((current) => current.map((item) => (
          item.id === notification.id ? { ...item, read_at: result.read_at } : item
        )))
        setUnreadCount((current) => Math.max(0, current - 1))
      } catch (requestError) {
        setError(requestError.message)
        return
      }
    }
    setOpen(false)
    onNavigate('bookings')
  }

  const markAllRead = async () => {
    try {
      const result = await api.markAllNotificationsRead(token)
      setItems((current) => current.map((item) => ({ ...item, read_at: item.read_at || result.read_at })))
      setUnreadCount(0)
      setError('')
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return (
    <div className="notification-center" ref={rootRef}>
      <button
        ref={triggerRef}
        className={`icon-button notification-trigger ${open ? 'notification-trigger--active' : ''}`}
        type="button"
        onClick={openPanel}
        aria-label="Thông báo"
        aria-expanded={open}
        aria-controls="internal-notification-panel"
        title="Thông báo"
      >
        <Bell size={20} weight={unreadCount ? 'fill' : 'regular'} />
        {unreadCount > 0 && <span className="notification-badge">{unreadCount > 99 ? '99+' : unreadCount}</span>}
      </button>

      {open && (
        <div ref={panelRef} id="internal-notification-panel" className="notification-panel" role="dialog" aria-label="Thông báo nội bộ" tabIndex={-1}>
          <div className="notification-panel__header">
            <div>
              <strong>Thông báo</strong>
              <span>{unreadCount ? `${unreadCount} chưa đọc` : 'Đã đọc tất cả'}</span>
            </div>
            {unreadCount > 0 && (
              <button className="text-button notification-read-all" type="button" onClick={markAllRead}>
                <Check size={16} /> Đọc tất cả
              </button>
            )}
          </div>

          <div className="notification-list">
            {loading && <div className="notification-state"><SpinnerGap className="spin" size={20} /> Đang tải</div>}
            {!loading && error && <div className="notification-state notification-state--error">{error}</div>}
            {!loading && !error && items.length === 0 && (
              <div className="notification-state"><Bell size={21} /> Chưa có thông báo</div>
            )}
            {!loading && !error && items.map((notification) => (
              <button
                key={notification.id}
                className={`notification-item ${notification.read_at ? '' : 'notification-item--unread'}`}
                type="button"
                onClick={() => openNotification(notification)}
              >
                <span className="notification-item__icon"><CalendarCheck size={18} weight="duotone" /></span>
                <span className="notification-item__copy">
                  <strong>{notification.title}</strong>
                  <span>{notification.body}</span>
                  <small>{formatDateTime(notification.created_at)}</small>
                </span>
                {!notification.read_at && <span className="notification-item__dot" aria-label="Chưa đọc" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
