import lacHongSide from '../media/lachong-side.webp'

/**
 * Popup nhỏ hiện khi đang chờ LLM sinh brief khách hàng cho sales (BookingsPage).
 * Xe đứng yên giữa khung — chỉ bánh xe (spin quầng sáng) và vệt gió phía sau tạo cảm giác
 * chuyển động, tránh nhầm với hiệu ứng 3D lớn ở trang chủ (khối đó đã bị bác bỏ, xem
 * memory p053-heritage-corridor — khối này CHỦ Ý nhỏ và chỉ là ảnh tĩnh + CSS, không phải 3D).
 */
export function BriefLoadingOverlay() {
  return (
    <div className="brief-loading-overlay" role="status" aria-live="polite">
      <div className="brief-loading-card">
        <div className="brief-loading-stage">
          <span className="brief-wind brief-wind--1" />
          <span className="brief-wind brief-wind--2" />
          <span className="brief-wind brief-wind--3" />
          <span className="brief-car__shadow" />
          <div className="brief-car">
            <img src={lacHongSide} alt="" aria-hidden="true" />
            <span className="brief-car__wheel brief-car__wheel--rear" />
            <span className="brief-car__wheel brief-car__wheel--front" />
          </div>
        </div>
        <strong>Đang tạo brief cho sales…</strong>
        <span>Hệ thống đang tổng hợp thông tin khách hàng, việc này mất vài giây.</span>
      </div>
    </div>
  )
}
