import { useEffect, useState } from 'react'
import { api } from './api.js'
import { PageState } from './components/PageState.jsx'
import { Shell } from './components/Shell.jsx'
import { AuditPage, CatalogPage, NetworkPage } from './pages/ReferencePages.jsx'
import { BookingsPage } from './pages/BookingsPage.jsx'
import { DashboardPage } from './pages/DashboardPage.jsx'
import { FleetPage } from './pages/FleetPage.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { ShowroomSchedulePage } from './pages/ShowroomSchedulePage.jsx'
import { TeamPage } from './pages/TeamPage.jsx'
import { TransfersPage } from './pages/TransfersPage.jsx'
import { UsersPage } from './pages/UsersPage.jsx'

const TOKEN_KEY = 'p053_internal_token'
const PAGE_IDS = new Set(['dashboard', 'bookings', 'team', 'fleet', 'schedule', 'network', 'catalog', 'transfers', 'audit', 'users'])
const PAGE_ACCESS = {
  staff: new Set(['dashboard', 'bookings', 'team']),
  showroom_manager: new Set(['dashboard', 'bookings', 'team', 'fleet', 'schedule', 'audit']),
  operations_admin: PAGE_IDS,
}

const pageFromLocation = () => {
  const candidate = window.location.pathname.replace(/^\/+|\/+$/g, '')
  return PAGE_IDS.has(candidate) ? candidate : 'dashboard'
}

const pagePath = (page) => (page === 'dashboard' ? '/' : `/${page}`)

export default function App() {
  const [token, setToken] = useState(() => {
    localStorage.removeItem(TOKEN_KEY)
    return sessionStorage.getItem(TOKEN_KEY) || ''
  })
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(token))
  const [sessionError, setSessionError] = useState('')
  const [page, setPage] = useState(pageFromLocation)

  useEffect(() => {
    const syncFromHistory = () => setPage(pageFromLocation())
    window.addEventListener('popstate', syncFromHistory)
    return () => window.removeEventListener('popstate', syncFromHistory)
  }, [])

  useEffect(() => {
    if (!token) { setLoading(false); setUser(null); return }
    let active = true
    setLoading(true)
    api.me(token).then((profile) => { if (active) { setUser(profile); setSessionError('') } }).catch((error) => {
      if (active) { sessionStorage.removeItem(TOKEN_KEY); setToken(''); setUser(null); setSessionError(error.message) }
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token])

  const login = async (username, password) => {
    const session = await api.login(username, password)
    sessionStorage.setItem(TOKEN_KEY, session.access_token)
    setUser(session.user)
    setToken(session.access_token)
    const requestedPage = pageFromLocation()
    const nextPage = PAGE_ACCESS[session.user.role]?.has(requestedPage) ? requestedPage : 'dashboard'
    setPage(nextPage)
    if (nextPage !== requestedPage) window.history.replaceState(null, '', pagePath(nextPage))
  }

  const logout = async () => {
    try { await api.logout(token) } catch { /* Session may already be expired. */ }
    sessionStorage.removeItem(TOKEN_KEY)
    setToken(''); setUser(null); setPage('dashboard')
    window.history.replaceState(null, '', '/')
  }

  useEffect(() => {
    if (!user || PAGE_ACCESS[user.role]?.has(page)) return
    setPage('dashboard')
    window.history.replaceState(null, '', '/')
  }, [page, user])

  const navigate = (nextPage) => {
    if (!PAGE_ACCESS[user?.role]?.has(nextPage)) return
    if (nextPage !== page) window.history.pushState(null, '', pagePath(nextPage))
    setPage(nextPage)
  }

  if (loading) return <div className="app-loading"><PageState loading /></div>
  if (!token || !user) return <><LoginPage onLogin={login} />{sessionError && <div className="session-toast">{sessionError}</div>}</>

  const currentPage = PAGE_ACCESS[user.role]?.has(page) ? page : 'dashboard'

  const pages = {
    dashboard: <DashboardPage token={token} user={user} />,
    bookings: <BookingsPage token={token} user={user} />,
    team: <TeamPage token={token} user={user} />,
    fleet: <FleetPage token={token} user={user} />,
    schedule: <ShowroomSchedulePage token={token} user={user} />,
    network: <NetworkPage token={token} />,
    catalog: <CatalogPage token={token} />,
    transfers: <TransfersPage token={token} />,
    audit: <AuditPage token={token} />,
    users: <UsersPage token={token} />,
  }

  return <Shell token={token} user={user} page={currentPage} onNavigate={navigate} onLogout={logout}>{pages[currentPage]}</Shell>
}
