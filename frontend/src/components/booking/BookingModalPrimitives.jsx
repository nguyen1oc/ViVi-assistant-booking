/**
 * components/booking/BookingModalPrimitives.jsx
 *
 * Modals shown at the beginning and end of the booking demo flow:
 * - RecipientModal: Choice modal for self, other, lookup, or demo
 * - ResumeModal: Choice modal for resuming an uncompleted session
 * - DemoCompletionModal: Clean completion popup with 2/3 real experience (left) and 1/3 cancel (right)
 */
import { ArrowLeft, ArrowRight, CalendarBlank, Clock, PlayCircle, User, UserPlus, X } from '@phosphor-icons/react'
import { useDialogFocus } from '../../hooks/useDialogFocus'

export function RecipientModal({ onSelect, onLookup, onDemo, onBack }) {
  const dialogRef = useDialogFocus()

  return (
    <div
      ref={dialogRef}
      className="recipient-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="recipient-title"
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onBack()
      }}
    >
      <div className="recipient-modal__panel">
        <button className="recipient-modal__back" type="button" onClick={onBack} aria-label="Quay lại trang vừa xem" title="Quay lại trang vừa xem">
          <ArrowLeft size={18} weight="bold" aria-hidden="true" />
        </button>
        <span className="recipient-modal__mark"><User size={24} weight="light" /></span>
        <p>Trước khi bắt đầu</p>
        <h1 id="recipient-title">Bạn muốn làm gì <span className="no-orphan">hôm nay?</span></h1>
        <div className="recipient-modal__choices">
          <button type="button" onClick={() => onSelect('self')}>
            <User size={24} weight="light" />
            <span><strong>Đặt lịch cho chính tôi</strong><small>Người đặt lịch cũng là người lái thử</small></span>
            <ArrowRight size={18} weight="light" />
          </button>
          <button type="button" onClick={() => onSelect('other')}>
            <UserPlus size={24} weight="light" />
            <span><strong>Đặt hộ người khác</strong><small>Lưu riêng thông tin người đặt và người lái</small></span>
            <ArrowRight size={18} weight="light" />
          </button>
          <button type="button" onClick={onLookup}>
            <CalendarBlank size={24} weight="light" />
            <span><strong>Tra cứu lịch đã đặt</strong><small>Xem lại, đổi giờ hoặc huỷ lịch của bạn</small></span>
            <ArrowRight size={18} weight="light" />
          </button>
          {onDemo && (
            <button
              type="button"
              className="recipient-modal__choice--demo"
              onClick={onDemo}
            >
              <PlayCircle size={24} weight="light" />
              <span>
                <strong>Xem demo luồng chuẩn (Happy Path)</strong>
                <small>Mô phỏng tự động quy trình từ tư vấn đến xuất vé</small>
              </span>
              <ArrowRight size={18} weight="light" />
            </button>
          )}
        </div>
        <small>Bạn có thể thay đổi thông tin trước khi xác nhận cuối cùng.</small>
      </div>
    </div>
  )
}

export function ResumeModal({ onContinue, onRestart, onBack }) {
  const dialogRef = useDialogFocus()

  return (
    <div
      ref={dialogRef}
      className="recipient-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="resume-title"
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onBack()
      }}
    >
      <div className="recipient-modal__panel booking-resume-modal">
        <button className="recipient-modal__back" type="button" onClick={onBack} aria-label="Về trang chủ" title="Về trang chủ">
          <ArrowLeft size={18} weight="bold" aria-hidden="true" />
        </button>
        <span className="recipient-modal__mark"><Clock size={24} weight="light" /></span>
        <p>Phiên trước chưa hoàn tất</p>
        <h1 id="resume-title">Bạn muốn tiếp tục lịch đang dở?</h1>
        <div className="recipient-modal__choices booking-resume-modal__choices">
          <button type="button" onClick={onContinue}><span><strong>Tiếp tục</strong><small>Quay lại bước bạn đang thực hiện</small></span><ArrowRight size={18} weight="light" /></button>
          <button type="button" onClick={onRestart}><span><strong>Làm mới</strong><small>Bắt đầu một lịch đặt mới</small></span><ArrowRight size={18} weight="light" /></button>
        </div>
      </div>
    </div>
  )
}

export function DemoCompletionModal({ onRestartRealSession, onClose }) {
  const dialogRef = useDialogFocus()

  return (
    <div
      ref={dialogRef}
      className="recipient-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-complete-title"
      tabIndex={-1}
    >
      <div
        className="recipient-modal__panel"
        style={{
          width: 'min(100%, 420px)',
          padding: '28px 30px 26px',
          borderRadius: '22px',
          textAlign: 'left',
          position: 'relative',
          background: '#f8f9f8',
          border: '1px solid rgba(255, 255, 255, 0.72)',
          boxShadow: 'inset 0 1px 0 #fff, 0 34px 90px -44px rgba(18, 24, 32, 0.6)',
        }}
      >
        <button
          className="recipient-modal__back"
          type="button"
          onClick={onClose}
          aria-label="Đóng"
          title="Đóng"
          style={{ top: '18px', right: '18px', width: '36px', height: '36px' }}
        >
          <X size={16} weight="bold" aria-hidden="true" />
        </button>
        <div style={{ margin: '0 0 6px', color: 'var(--blue, #1464f4)', fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.02em', textTransform: 'none' }}>
          Trải nghiệm hoàn tất
        </div>
        <h2 id="demo-complete-title" style={{ fontSize: '1.35rem', fontWeight: 560, margin: '0 0 10px', color: 'var(--ink, #171a20)', letterSpacing: '-0.035em', lineHeight: 1.25 }}>
          Bạn đã xem xong luồng mẫu
        </h2>
        <div style={{ fontSize: '0.88rem', color: 'var(--muted, #6b6f76)', margin: '0 0 24px', lineHeight: 1.55, textTransform: 'none' }}>
          ViVi đã cùng bạn đi qua các bước đặt lịch lái thử VinFast. Bạn có thể bắt đầu tạo lịch hẹn thật cho riêng mình ngay bây giờ.
        </div>
        <div style={{ display: 'flex', gap: '10px', width: '100%', alignItems: 'center' }}>
          <button
            type="button"
            onClick={onRestartRealSession}
            style={{
              flex: 2,
              height: '48px',
              borderRadius: '14px',
              border: 'none',
              background: 'var(--blue, #1464f4)',
              color: '#ffffff',
              fontSize: '0.92rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px -4px rgba(20, 100, 244, 0.45)',
              transition: 'background 0.2s var(--ease-soft), transform 0.15s var(--ease-soft)',
            }}
          >
            Trải nghiệm thực tế
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              flex: 1,
              height: '48px',
              borderRadius: '14px',
              border: '1px solid var(--line, rgba(23, 26, 32, 0.14))',
              background: '#ffffff',
              color: 'var(--ink, #171a20)',
              fontSize: '0.92rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.2s var(--ease-soft), border-color 0.2s var(--ease-soft)',
            }}
          >
            Hủy
          </button>
        </div>
      </div>
    </div>
  )
}
