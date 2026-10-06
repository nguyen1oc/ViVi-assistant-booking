import { ArrowRight, LockKey, ShieldCheck, UserCircle } from '@phosphor-icons/react'
import { useState } from 'react'
import lacHongBg from '../media/lachong-login-bg.webp'
import vinfastLogo from '../media/vinfast-logo.webp'

export function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onLogin(username, password)
    } catch (caught) {
      setError(caught.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-story">
        <img className="login-story__watermark" src={lacHongBg} alt="" aria-hidden="true" />
        <div className="login-story__glow" />
        <div className="login-story__brand"><img src={vinfastLogo} alt="VinFast" /> DriveOps</div>
        <div className="login-story__content">
          <span className="login-kicker">Test Drive Operations</span>
          <h1>Một nhịp vận hành.<br />Mọi showroom.</h1>
          <p>Theo dõi lịch lái thử, ca nhân viên và đội xe demo trong một không gian được phân quyền rõ ràng.</p>
          <div className="login-proof">
            <div><ShieldCheck size={21} weight="fill" /><span>RBAC theo vai trò</span></div>
            <div><LockKey size={21} weight="fill" /><span>Giới hạn theo showroom</span></div>
          </div>
        </div>
        <div className="login-story__foot">P053 · VinUni Capstone</div>
      </section>
      <section className="login-panel">
        <form className="login-form" onSubmit={submit}>
          <div className="login-form__icon"><UserCircle size={31} weight="duotone" /></div>
          <span className="eyebrow">Cổng thông tin nội bộ</span>
          <h2>Chào mừng trở lại</h2>
          <p className="muted">Đăng nhập bằng tài khoản đã được Operations Admin cấp.</p>
          <label>
            <span>Tên đăng nhập</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" placeholder="staff.name" required />
          </label>
          <label>
            <span>Mật khẩu</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" placeholder="••••••••••••" required />
          </label>
          {error && <div className="form-error">{error}</div>}
          <button className="primary-button primary-button--wide" disabled={loading}>
            <span>{loading ? 'Đang xác thực…' : 'Đăng nhập an toàn'}</span>
            {!loading && <ArrowRight size={19} />}
          </button>
          <small>Phiên làm việc sẽ tự hết hạn và có thể được thu hồi từ backend.</small>
        </form>
      </section>
    </main>
  )
}
