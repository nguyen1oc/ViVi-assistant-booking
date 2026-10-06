import { useEffect, useState } from 'react'
import { ArrowLeft } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import lacHongWatermark from '../media/local/email/lac-hong-watermark.jpg'
import { vehicleImage } from '../media/assets'

const vinfastWordmark = vehicleImage('Vinfast-logo-new_NO_Tagline -2D-Horizontal black.png')

const EMAIL_COPY = {
  confirmation: {
    label: 'Mail xác nhận',
    headline: ['Phiếu xác nhận', 'lịch hẹn'],
    intro: 'Lịch lái thử VinFast VF 9 Plus của bạn đã được xác nhận. Thông tin chi tiết được ghi lại bên dưới.',
    note: 'Đội ngũ VinFast sẽ chuẩn bị xe trước giờ hẹn. Bạn có thể mở thiệp mời để xem lại đầy đủ thời gian và địa điểm.',
  },
  reschedule: {
    label: 'Mail đổi giờ',
    headline: ['Lịch hẹn', 'đã đổi giờ'],
    intro: 'Yêu cầu đổi giờ của bạn đã được xác nhận. Lịch lái thử VinFast VF 9 Plus hiện được cập nhật theo thời gian mới.',
    note: 'Đây là thời gian mới nhất của lịch hẹn. Thiệp mời của bạn vẫn giữ nguyên đường dẫn và đã hiển thị thông tin vừa cập nhật.',
  },
}

export function InvitationEmailPreviewPage() {
  const [mode, setMode] = useState('confirmation')
  const copy = EMAIL_COPY[mode]

  useEffect(() => {
    const previousTitle = document.title
    document.title = 'Xem trước email có thiệp mời | VinFast'
    return () => { document.title = previousTitle }
  }, [])

  return (
    <main className="email-preview-page">
      <div className="email-preview-toolbar">
        <Link to="/invitation-preview">
          <ArrowLeft size={18} weight="light" aria-hidden="true" />
          Xem thiệp mời
        </Link>
        <div className="email-preview-tabs" role="group" aria-label="Chọn loại email xem trước">
          {Object.entries(EMAIL_COPY).map(([key, item]) => (
            <button
              key={key}
              type="button"
              className={mode === key ? 'is-active' : ''}
              aria-pressed={mode === key}
              onClick={() => setMode(key)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <p className="email-preview-caption">Bản dựng giao diện trong trình duyệt. Chưa kết nối hệ thống gửi mail.</p>

      <article className="email-preview" aria-label={`Xem trước ${copy.label.toLowerCase()}`}>
        <header className="email-preview__brand-band">
          <img src={vinfastWordmark} alt="VinFast" />
        </header>

        <div className="email-preview__heading">
          <h1>{copy.headline[0]}<br />{copy.headline[1]}</h1>
        </div>

        <div className="email-preview__name">Nguyễn Hoàng Minh</div>

        <div className="email-preview__body">
          <p className="email-preview__intro">Xin chào Nguyễn Hoàng Minh,</p>
          <p className="email-preview__copy">{copy.intro}</p>

          <section className="email-preview__card" style={{ '--email-card-watermark': `url(${lacHongWatermark})` }}>
            <h2>Thông tin<br />lịch hẹn</h2>

            <dl className="email-preview__facts">
              {mode === 'reschedule' && (
                <div>
                  <dt>Giờ trước đây</dt>
                  <dd><s>14:30, Thứ Tư<br />26.08.2026</s></dd>
                </div>
              )}
              <div>
                <dt>{mode === 'reschedule' ? 'Giờ mới' : 'Thời gian'}</dt>
                <dd><strong>09:30, Thứ Sáu</strong><br />28.08.2026</dd>
              </div>
              <div>
                <dt>Mẫu xe</dt>
                <dd>VinFast VF 9 Plus</dd>
              </div>
              <div>
                <dt>Showroom</dt>
                <dd>VinFast Landmark 81<br />208 Nguyễn Hữu Cảnh, TP.HCM</dd>
              </div>
            </dl>

            <p className="email-preview__note">{copy.note}</p>

            <div className="email-preview__actions">
              <Link className="email-preview__action email-preview__action--secondary" to="/booking">
                <span className="email-preview__action-label--full">Đến trang đặt lịch VinFast</span>
                <span className="email-preview__action-label--short">Trang đặt lịch</span>
              </Link>
              <Link className="email-preview__action email-preview__action--primary" to="/invitation-preview">
                <span className="email-preview__action-label--full">Xem thiệp mời của bạn</span>
                <span className="email-preview__action-label--short">Xem thiệp mời</span>
              </Link>
            </div>
          </section>
        </div>

        <footer className="email-preview__footer">
          <img src={vinfastWordmark} alt="" aria-hidden="true" />
          <p>VinFast trân trọng cảm ơn bạn.</p>
          <p>© 2026 VinFast</p>
        </footer>
      </article>
    </main>
  )
}
