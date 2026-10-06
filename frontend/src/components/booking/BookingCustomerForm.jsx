/**
 * components/booking/BookingCustomerForm.jsx — Form nhập thông tin khách (bước 5, trong khung chat ViVi).
 *
 * ✅ ĐANG DÙNG THẬT: BookingPage.jsx import dưới tên CustomerForm.
 *
 * Form đổi hình theo prop `recipient`:
 * - recipient = 'self'  → 3 ô: Họ và tên · Email · Số điện thoại.
 * - recipient = 'other' → thêm "Tên người lái thử", 2 nhãn đổi thành
 *   "Tên người đặt lịch" / "Email nhận OTP", và MỘT KHỐI LIÊN HỆ RIÊNG cho người lái.
 *
 * KHỐI LIÊN HỆ NGƯỜI LÁI (chỉ ở nhánh đặt hộ): mặc định tick "dùng chung liên hệ với
 * người đặt". Bỏ tick thì hiện 2 ô email + SĐT riêng cho người lái. Trước đây form không
 * có phần này, nên dù đã tách TÊN thì email và SĐT vẫn bị gán chung của người đặt —
 * showroom gọi nhầm người, và người cầm lái không nhận được thông báo nào.
 *
 * Ngoài ra có 2 ô tick: xác nhận có giấy phép lái xe (BẮT BUỘC, sai thì báo lỗi đỏ)
 * và đồng ý nhận thông tin ưu đãi (mặc định đã tick sẵn).
 *
 * KHÔNG có ô tải ảnh GPLX ở đây và đừng thêm vào — chỉ cần lời cam kết.
 *
 * File này chỉ hiển thị. Toàn bộ việc kiểm tra dữ liệu và báo lỗi nằm ở hàm submitPerson()
 * trong BookingPage.jsx — muốn đổi quy tắc validate thì sửa bên đó.
 */
import { ArrowRight, Check } from '@phosphor-icons/react'
import { EMAIL_MAX_LENGTH, NAME_MAX_LENGTH, PHONE_LENGTH } from '../../utils/contactValidation'

export function BookingCustomerForm({ recipient, value, errors, disabled = false, busy = false, onChange, onSubmit, onBack }) {
  const bookingForOther = recipient === 'other'
  const shareContact = value.driverSameContact !== false

  return (
    <form className={`vivi-customer-form ${disabled ? 'is-readonly' : ''}`} onSubmit={(event) => {
      if (disabled) {
        event.preventDefault()
        return
      }
      onSubmit(event)
    }} noValidate aria-disabled={disabled}>
      <div className="vivi-customer-form__grid">
        <label><span>{bookingForOther ? 'Tên người đặt lịch' : 'Họ và tên'} <span style={{ color: '#ef4444' }}>*</span></span><input name="booking-name" autoComplete="name" maxLength={NAME_MAX_LENGTH} value={value.bookingName} disabled={disabled} required onChange={(event) => onChange('bookingName', event.target.value)} aria-invalid={Boolean(errors.bookingName)} aria-describedby={errors.bookingName ? 'booking-name-error' : undefined} />{errors.bookingName && <small id="booking-name-error" role="alert">{errors.bookingName}</small>}</label>
        {bookingForOther && <label><span>Tên người lái thử <span style={{ color: '#ef4444' }}>*</span></span><input name="driver-name" autoComplete="off" maxLength={NAME_MAX_LENGTH} value={value.driverName} disabled={disabled} required onChange={(event) => onChange('driverName', event.target.value)} aria-invalid={Boolean(errors.driverName)} aria-describedby={errors.driverName ? 'driver-name-error' : undefined} />{errors.driverName && <small id="driver-name-error" role="alert">{errors.driverName}</small>}</label>}
        <label><span>Email <span style={{ color: '#ef4444' }}>*</span></span><input name="email" type="email" inputMode="email" autoComplete="email" maxLength={EMAIL_MAX_LENGTH} placeholder="tenban@example.com" value={value.email} disabled={disabled} onChange={(event) => onChange('email', event.target.value)} required aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'booking-email-error' : undefined} />{errors.email && <small id="booking-email-error" role="alert">{errors.email}</small>}</label>
        <label><span>Số điện thoại</span><input name="tel" type="tel" inputMode="numeric" autoComplete="tel" maxLength={PHONE_LENGTH} placeholder="09xxxxxxxx" value={value.phone} disabled={disabled} onChange={(event) => onChange('phone', event.target.value)} aria-invalid={Boolean(errors.phone)} aria-describedby={errors.phone ? 'booking-phone-error' : undefined} />{errors.phone && <small id="booking-phone-error" role="alert">{errors.phone}</small>}</label>
      </div>

      {bookingForOther && (
        <fieldset className="vivi-driver-contact">
          <legend>Liên hệ của người lái thử</legend>
          <label className="license-check">
            <input
              type="checkbox"
              checked={shareContact}
              disabled={disabled}
              onChange={(event) => onChange('driverSameContact', event.target.checked)}
            />
            <span><Check size={14} weight="bold" /></span>
            <p>{value.driverName?.trim() || 'Người lái thử'} dùng chung <strong>email và số điện thoại</strong> với tôi.</p>
          </label>

          {!shareContact && (
            <>
              <p className="vivi-driver-contact__note">
                Showroom sẽ liên hệ trực tiếp với người lái theo thông tin dưới đây.
              </p>
              <div className="vivi-customer-form__grid">
                <label><span>Email người lái <span style={{ color: '#ef4444' }}>*</span></span><input name="driver-email" type="email" inputMode="email" autoComplete="off" maxLength={EMAIL_MAX_LENGTH} placeholder="nguoilai@example.com" value={value.driverEmail} disabled={disabled} required onChange={(event) => onChange('driverEmail', event.target.value)} aria-invalid={Boolean(errors.driverEmail)} aria-describedby={errors.driverEmail ? 'driver-email-error' : undefined} />{errors.driverEmail && <small id="driver-email-error" role="alert">{errors.driverEmail}</small>}</label>
                <label><span>Số điện thoại người lái</span><input name="driver-phone" type="tel" inputMode="numeric" autoComplete="off" maxLength={PHONE_LENGTH} placeholder="09xxxxxxxx" value={value.driverPhone} disabled={disabled} onChange={(event) => onChange('driverPhone', event.target.value)} aria-invalid={Boolean(errors.driverPhone)} aria-describedby={errors.driverPhone ? 'driver-phone-error' : undefined} />{errors.driverPhone && <small id="driver-phone-error" role="alert">{errors.driverPhone}</small>}</label>
              </div>
            </>
          )}
        </fieldset>
      )}
      <label className={`license-check ${errors.hasLicense ? 'has-error' : ''}`}><input type="checkbox" checked={value.hasLicense} disabled={disabled} onChange={(event) => onChange('hasLicense', event.target.checked)} required aria-invalid={Boolean(errors.hasLicense)} aria-describedby={errors.hasLicense ? 'license-error' : undefined} /><span><Check size={14} weight="bold" /></span><p>Tôi xác nhận người lái thử <strong>có giấy phép lái xe</strong> phù hợp với mẫu xe đăng ký <span style={{ color: '#ef4444' }}>*</span>.</p></label>
      {errors.hasLicense && <small id="license-error" className="vivi-customer-form__license-error" role="alert">{errors.hasLicense}</small>}
      <label className="license-check"><input type="checkbox" checked={value.marketingConsent} disabled={disabled} onChange={(event) => onChange('marketingConsent', event.target.checked)} /><span><Check size={14} weight="bold" /></span><p>Tôi đồng ý nhận <strong>thông tin ưu đãi</strong>, <strong>khuyến mãi</strong> và <strong>sự kiện mới nhất</strong> từ VinFast.</p></label>
      {/* Cặp nút đi liền nhau, đúng như màn xem lại phiếu (.vivi-review-actions): nút chính
          bên trái, lối lùi bên phải. Trước đây bước này chỉ có mỗi nút chính nên vào tới form
          là kẹt — muốn đổi khung giờ phải tự mò sang bảng bên trái.

          Nhãn "Chỉnh lại thông tin" là chữ anh Minh chọn, dùng chung với nút cùng vai ở màn xem
          lại phiếu. Nút đưa về bảng lịch bên trái, nơi đổi được khung giờ / showroom / mẫu xe —
          tức mọi lựa chọn đã chốt TRƯỚC bước điền form này. */}
      <div className="vivi-customer-form__actions">
        <button type="submit" disabled={disabled}>{busy ? 'Đang lưu thông tin...' : disabled ? 'Hồ sơ mẫu trong demo' : 'Tạo phiếu để kiểm tra'} <ArrowRight size={16} weight="light" /></button>
        {onBack && (
          <button type="button" onClick={onBack} disabled={disabled}>Hủy</button>
        )}
      </div>
    </form>
  )
}
