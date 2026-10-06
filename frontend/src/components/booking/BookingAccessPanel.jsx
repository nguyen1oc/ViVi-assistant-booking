/**
 * components/booking/BookingAccessPanel.jsx — Luồng TRA CỨU / SỬA / HUỶ lịch đã đặt, xác thực bằng OTP.
 *
 * ✅ ĐANG DÙNG THẬT: BookingPage.jsx render trong khung chat ViVi.
 *
 * Một component đổi thành 4 màn theo prop `phase`:
 * - 'request'        → nhập email và mã lịch tùy chọn rồi gửi OTP (có đếm ngược chống spam).
 * - (mặc định)       → 6 ô nhập OTP, tự nhảy ô. Dán đủ 6 số là TỰ XÁC THỰC luôn, không cần bấm nút.
 * - 'edit'           → sau khi xác thực: sửa Họ tên / SĐT / Email. Mã lịch để chỉ đọc, nền xám.
 * - 'confirm_cancel' → xem lại đầy đủ thông tin lịch rồi xác nhận huỷ (nút chữ đỏ).
 *
 * Đổi ngày giờ KHÔNG nằm ở đây nữa — nó đã chuyển sang tab "Lịch đã đặt" trong BookingPage.jsx.
 *
 * ⚠️ Cần dọn khi rảnh: file này viết style trực tiếp bằng inline style (biến actionStyle,
 * hoverBorder, các thuộc tính background/color rải rác) thay vì dùng class trong index.css
 * như phần còn lại của dự án. Muốn đổi màu/khoảng cách các nút ở đây thì phải sửa trong file,
 * không tìm thấy trong index.css đâu.
 */
import { EMAIL_MAX_LENGTH, NAME_MAX_LENGTH, PHONE_LENGTH } from '../../utils/contactValidation'

const actionStyle = { border: '1px solid transparent', background: '#f1f3f5', color: '#27313a', borderRadius: '8px', minHeight: '42px', cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }
const hoverBorder = (event) => { event.currentTarget.style.borderColor = '#1677ff' }
const leaveBorder = (event) => { event.currentTarget.style.borderColor = 'transparent' }

export function BookingAccessPanel({ phase, value, onChange, onRequest, onVerify, onResend, onCancelAccess, onCloseDetails, secondsLeft, resendLeft, error, busy, profile, canUpdate, onProfileChange, onProfileSave, onBookingCancel }) {
  const actions = (items) => <div style={{ display: 'grid', gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))`, gap: '8px', marginTop: '8px' }}>{items}</div>
  if (phase === 'request') return <form className="vivi-customer-form" onSubmit={onRequest}><div className="vivi-customer-form__grid booking-access-request-grid"><label><span>Email đăng ký <span style={{ color: '#ef4444' }}>*</span></span><input name="lookup-email" type="email" inputMode="email" autoComplete="email" maxLength={EMAIL_MAX_LENGTH} value={value.email} onChange={(event) => onChange('email', event.target.value)} placeholder="tenban@example.com" required /></label><label><span>Mã lịch</span><input name="lookup-booking-code" type="text" autoCapitalize="characters" autoComplete="off" value={value.bookingCode} onChange={(event) => onChange('bookingCode', event.target.value.toUpperCase())} placeholder="Ví dụ: VF260825ABC123" /></label></div><small style={{ display: 'block', marginTop: '8px', color: '#7b8188', lineHeight: 1.45 }}>Có mã lịch, ViVi sẽ mở thẳng đúng lịch. Không nhớ mã, bạn vẫn có thể tra cứu tất cả lịch bằng email.</small>{error && <small role="alert">{error}</small>}{actions([<button key="send" type="submit" disabled={busy || resendLeft > 0} style={actionStyle} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>{resendLeft > 0 ? `Gửi OTP sau ${resendLeft}s` : 'Gửi OTP qua email'}</button>, <button key="cancel" type="button" onClick={onCancelAccess} style={actionStyle} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>Hủy</button>])}</form>

  if (phase === 'edit' && profile) return <form className="vivi-customer-form" onSubmit={onProfileSave}><p>Thông tin khách hàng</p><div className="vivi-customer-form__grid"><label><span>Mã lịch</span><input value={profile.bookingCode} readOnly style={{ background: '#eef0f2', color: '#6b7280' }} /></label><label><span>Họ tên <span style={{ color: '#ef4444' }}>*</span></span><input maxLength={NAME_MAX_LENGTH} value={profile.bookerName} onChange={(event) => onProfileChange('bookerName', event.target.value)} readOnly={!canUpdate} required /></label><label><span>Email <span style={{ color: '#ef4444' }}>*</span></span><input type="email" maxLength={EMAIL_MAX_LENGTH} value={profile.email} onChange={(event) => onProfileChange('email', event.target.value)} readOnly={!canUpdate} required /></label><label><span>Số điện thoại</span><input type="tel" inputMode="numeric" maxLength={PHONE_LENGTH} value={profile.phone} onChange={(event) => onProfileChange('phone', event.target.value)} readOnly={!canUpdate} /></label></div>{error && <small role="alert">{error}</small>}{actions([...(canUpdate ? [<button key="save" type="submit" disabled={busy} style={actionStyle} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>Cập nhật thông tin</button>] : []), <button key="cancel" type="button" onClick={onCloseDetails} style={actionStyle} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>Đóng</button>])}</form>

  if (phase === 'confirm_cancel' && profile) return <section className="vivi-customer-form"><p>Thông tin lịch đã đặt</p><div className="vivi-customer-form__grid"><label><span>Mã lịch</span><input value={profile.bookingCode} readOnly style={{ background: '#eef0f2', color: '#6b7280' }} /></label><label><span>Người đặt lịch</span><input value={profile.bookerName} readOnly /></label><label><span>Người lái thử</span><input value={profile.driverName} readOnly /></label><label><span>Điện thoại</span><input value={profile.phone} readOnly /></label><label><span>Email</span><input value={profile.email} readOnly /></label><label><span>Mẫu xe</span><input value={profile.vehicleName} readOnly /></label><label><span>Showroom</span><input value={profile.showroomName} readOnly /></label><label><span>Thời gian</span><input value={`${profile.slotTime} · ${profile.slotDate}`} readOnly /></label></div><p style={{ margin: '14px 0 0', color: '#b42318' }}>Bạn có chắc muốn hủy lịch lái thử này không?</p>{error && <small role="alert">{error}</small>}{actions([<button key="confirm" type="button" onClick={onBookingCancel} disabled={busy} style={{ ...actionStyle, color: '#b42318' }} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>Xác nhận hủy lịch</button>, <button key="back" type="button" onClick={onCloseDetails} style={actionStyle} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>Giữ lại lịch</button>])}</section>

  const digits = Array.from({ length: 6 }, (_, index) => value.otpCode[index] || '')
  const setOtp = (raw) => onChange('otpCode', raw.replace(/\D/g, '').slice(0, 6))
  const updateDigit = (index, raw) => {
    const digit = raw.replace(/\D/g, '').slice(-1)
    const next = digits.map((current, i) => i === index ? digit : current).join('')
    setOtp(next)
    if (digit && index < 5) document.getElementById(`booking-otp-${index + 1}`)?.focus()
  }
  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace') {
      if (!digits[index] && index > 0) {
        event.preventDefault()
        const prevIndex = index - 1
        const next = digits.map((current, i) => i === prevIndex ? '' : current).join('')
        setOtp(next)
        document.getElementById(`booking-otp-${prevIndex}`)?.focus()
      }
    }
  }
  const pasteOtp = (event) => { const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6); if (pasted) { event.preventDefault(); setOtp(pasted); document.getElementById(`booking-otp-${Math.min(pasted.length, 6) - 1}`)?.focus(); if (pasted.length === 6 && !busy && secondsLeft > 0) onVerify(pasted) } }
  const resendCopy = secondsLeft <= 0 ? 'Mã OTP đã hết hạn · Gửi lại OTP' : resendLeft > 0 ? `Gửi lại OTP sau ${resendLeft}s` : 'Gửi lại OTP'
  return <div className="vivi-customer-form"><div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, minmax(0, 1fr))', gap: '8px', maxWidth: '378px', margin: '8px auto 3px' }}>{digits.map((digit, index) => <input key={index} id={`booking-otp-${index}`} aria-label={`Chữ số OTP ${index + 1}`} inputMode="numeric" maxLength="1" value={digit} onKeyDown={(event) => handleKeyDown(index, event)} onPaste={pasteOtp} onChange={(event) => updateDigit(index, event.target.value)} style={{ textAlign: 'center', fontSize: '1.25rem', fontWeight: 700, minHeight: '51px' }} />)}</div><div style={{ textAlign: 'center', margin: '2px 0 8px' }}><button type="button" onClick={onResend} disabled={busy || resendLeft > 0} style={{ display: 'inline', width: 'auto', border: 'none', background: 'transparent', color: '#69a8ea', cursor: resendLeft > 0 ? 'default' : 'pointer', fontWeight: 600, fontSize: '0.78rem', margin: 0, padding: 0 }} onMouseEnter={(event) => { if (!event.currentTarget.disabled) event.currentTarget.style.color = '#1677ff' }} onMouseLeave={(event) => { event.currentTarget.style.color = '#69a8ea' }}>{resendCopy}</button></div>{error && <small role="alert">{error}</small>}{actions([<button key="verify" type="button" onClick={() => onVerify()} disabled={busy || secondsLeft <= 0 || value.otpCode.length !== 6} style={actionStyle} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>Xác nhận</button>, <button key="cancel" type="button" onClick={onCancelAccess} style={actionStyle} onMouseEnter={hoverBorder} onMouseLeave={leaveBorder}>Hủy xác thực</button>])}</div>
}
