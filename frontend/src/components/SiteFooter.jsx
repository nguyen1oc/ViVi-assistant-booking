/**
 * components/SiteFooter.jsx — Chân trang dùng chung cho mọi trang marketing.
 *
 * Dùng ở: HomePage, CarDetailPage, AfterSalesPage, ChargingPage.
 * KHÔNG dùng ở BookingPage — trang đặt lịch cố ý không có chân trang để không cắt mạch thao tác.
 *
 * Chứa gì: tên thương hiệu, 5 link điều hướng và một dòng miễn trừ về thông số.
 * Hai link đầu là thẻ <a> dẫn tới anchor trên trang chủ (`/#models`, `/#technology`);
 * bốn link sau là <Link> của router. Đừng đổi <a> thành <Link> cho hai cái đầu — anchor
 * cần tải lại vị trí cuộn qua RouteEffects trong App.jsx.
 *
 * TODO [BACKEND/CMS]: Dòng miễn trừ và danh sách link đang hard-code. Khi có CMS, trả về
 * qua GET /api/v1/content/home dưới dạng block `footer` có `links[]` và `legalNotice`,
 * kèm `revision` để đối soát. Không trả HTML tự do.
 *
 * Style tương ứng: `.site-footer` trong index.css.
 */
import { Link } from 'react-router-dom'

export function SiteFooter({ showLearningNotice = false }) {
  return (
    <footer className="site-footer">
      <div className="section-frame site-footer__inner">
        <div>
          <strong>VINFAST</strong>
          <p>Thiết kế trải nghiệm xem xe và đặt lịch lái thử.</p>
        </div>
        <nav aria-label="Liên kết cuối trang">
          <a href="/#models">Ô tô</a>
          <a href="/#technology">Công nghệ</a>
          <Link to="/after-sales">Hậu mãi</Link>
          <Link to="/charging">Pin & trạm sạc</Link>
          {/* "Trợ lý ViVi" (/agent) đã bỏ: App.jsx chuyển hướng /agent → /booking, nên nó
              trùng đúng đích với "Đặt lịch" ngay bên cạnh.
              "Tra cứu lịch" thì KHÁC đích thật (?lookup=1 mở bước xác thực để xem/đổi/huỷ),
              nên không phải link trùng. */}
          <Link to="/booking">Đặt lịch</Link>
          <Link to="/booking?lookup=1">Tra cứu lịch</Link>
        </nav>
        <p className="site-footer__legal">
          Thông số được tổng hợp từ brochure chính thức và có thể thay đổi theo phiên bản, điều kiện vận hành hoặc chính sách của nhà sản xuất.
          {showLearningNotice && (
            <span className="site-footer__learning-notice">
              Website thử nghiệm phục vụ mục đích học tập.{' '}
              <a
                href="https://vinfastauto.com/vn_vi"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Truy cập website chính thức của VinFast (mở trong tab mới)"
              >
                Truy cập website chính thức của VinFast
              </a>.
            </span>
          )}
        </p>
      </div>
    </footer>
  )
}
