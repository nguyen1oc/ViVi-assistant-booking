/**
 * components/AppShell.jsx — Khung bao ngoài của mọi trang: header, menu và dải cảnh báo backend.
 *
 * Dùng ở: HomePage, CarDetailPage, AfterSalesPage, ChargingPage.
 * KHÔNG dùng ở BookingPage — trang đặt lịch cố ý có header riêng, gọn hơn.
 *
 * Chứa gì:
 * - Mảng `links` (dòng ~8) và `productGroups` (dòng ~16): TOÀN BỘ menu nằm ở 2 mảng này.
 *   Muốn thêm/xoá/đổi tên mục menu thì sửa ngay đây, không cần đụng chỗ khác.
 * - Header sticky + logo + mega-menu "Ô tô" (2 nhóm: Động cơ điện / Dòng xe dịch vụ).
 * - Nút "Đặt lịch lái thử": đang ở /models/:id hoặc /cars/:id thì tự gắn ?car=<id> vào link,
 *   các trang khác dẫn thẳng /booking. Đây là CTA đặt lịch duy nhất trong header — đừng
 *   thêm mục menu nào cũng trỏ /booking nữa.
 * - Menu overlay cho mobile (nút hamburger), đóng bằng phím Esc.
 * - Dải băng vàng "Không thể kết nối backend" + nút thử lại.
 * - Link "Đi đến nội dung chính" cho người dùng bàn phím/screen reader.
 *
 * Style tương ứng: mục "Floating navigation" trong index.css.
 */
import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { ArrowUpRight, Buildings, CaretDown, CarProfile } from '@phosphor-icons/react'
import { Brand } from './Brand'
import { IslandButton } from './IslandButton'
import { useBackendStatus } from '../context/BackendStatusContext'
import { useDialogFocus } from '../hooks/useDialogFocus'

// KHÔNG thêm mục nào dẫn về /booking vào mảng này: nút "Đặt lịch lái thử" bên phải
// header luôn hiển thị (site-nav là position:fixed) nên một mục menu cùng đích chỉ làm
// người dùng phải chọn giữa hai thứ giống hệt nhau. ViVi là anchor nội dung trên trang
// chủ nên đứng cùng cấp, cùng kiểu chữ với Công nghệ / Hệ sinh thái — không biến thành CTA.
const links = [
  { label: 'ViVi', to: '/#vivi' },
  { label: 'Công nghệ', to: '/#technology' },
  { label: 'Hệ sinh thái', to: '/#ecosystem' },
  { label: 'Hậu mãi', to: '/after-sales' },
  { label: 'Pin & trạm sạc', to: '/charging' },
]

const productGroups = [
  { label: 'Động cơ điện', copy: 'Dải xe cá nhân từ VF 3 đến VF 9.', to: '/#models-electric', icon: CarProfile },
  { label: 'Dòng xe dịch vụ', copy: 'Green, giao vận và vận tải công cộng.', to: '/#models-service', icon: Buildings },
]

export function AppShell({ children, navTheme = 'light' }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [productsOpen, setProductsOpen] = useState(false)
  const menuDialogRef = useDialogFocus({ active: menuOpen, onClose: () => setMenuOpen(false) })
  const location = useLocation()
  // Đang đứng ở trang chi tiết xe thì nút đặt lịch phải mang theo đúng mẫu xe đó.
  // Trước đây href cố định là '/booking' nên nút nổi bật nhất trang lại là nút DUY NHẤT
  // làm rơi mẫu xe, trong khi hero, dock và CTA cuối trang đều gắn ?car=…
  const detailMatch = location.pathname.match(/^\/(?:models|cars)\/([^/]+)/)
  const bookingHref = detailMatch ? `/booking?car=${detailMatch[1]}` : '/booking'
  const { bookingStatus, retry } = useBackendStatus()

  useEffect(() => {
    setMenuOpen(false)
    setProductsOpen(false)
  }, [location.pathname, location.hash])

  useEffect(() => {
    if (!menuOpen) return undefined
    document.body.classList.add('menu-is-open')
    return () => {
      document.body.classList.remove('menu-is-open')
    }
  }, [menuOpen])

  useEffect(() => {
    if (!productsOpen) return undefined
    const closeProducts = (event) => {
      if (event.type === 'keydown' && event.key !== 'Escape') return
      if (event.type === 'pointerdown' && event.target.closest?.('.site-nav__products')) return
      setProductsOpen(false)
    }
    document.addEventListener('keydown', closeProducts)
    document.addEventListener('pointerdown', closeProducts)
    return () => {
      document.removeEventListener('keydown', closeProducts)
      document.removeEventListener('pointerdown', closeProducts)
    }
  }, [productsOpen])

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Đi đến nội dung chính
      </a>

      <header className={`site-nav site-nav--${navTheme}`}>
        <div className="site-nav__inner">
          <Brand inverse={navTheme === 'dark'} />

          <nav className="site-nav__links" aria-label="Điều hướng chính">
            <div className={`site-nav__products ${productsOpen ? 'is-open' : ''}`}>
              <button
                type="button"
                aria-expanded={productsOpen}
                aria-controls="vehicle-categories"
                onClick={() => setProductsOpen((open) => !open)}
              >
                Ô tô <CaretDown size={14} weight="light" />
              </button>
              <div id="vehicle-categories" className="vehicle-mega" aria-hidden={!productsOpen}>
                <div className="vehicle-mega__intro">
                  <span>Chọn cách bạn sử dụng xe</span>
                  <strong>Một catalogue, hai dòng sản phẩm rõ ràng.</strong>
                </div>
                <div className="vehicle-mega__links">
                  {productGroups.map(({ label, copy, to, icon: Icon }) => (
                    <Link to={to} key={label} tabIndex={productsOpen ? 0 : -1} onClick={() => setProductsOpen(false)}>
                      <Icon size={24} weight="light" />
                      <span><strong>{label}</strong><small>{copy}</small></span>
                      <ArrowUpRight size={17} weight="light" />
                    </Link>
                  ))}
                </div>
              </div>
            </div>
            {links.map((link) => (
              <Link key={link.label} to={link.to}>
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="site-nav__actions">
            <IslandButton to={bookingHref} variant="blue" className="site-nav__booking">
              Tra cứu và đặt lịch lái thử
            </IslandButton>
            <button
              className={`menu-toggle ${menuOpen ? 'is-open' : ''}`}
              type="button"
              aria-label={menuOpen ? 'Đóng trình đơn' : 'Mở trình đơn'}
              aria-expanded={menuOpen}
              aria-controls="mobile-navigation"
              onClick={() => setMenuOpen((open) => !open)}
            >
              <span />
              <span />
            </button>
          </div>
        </div>
      </header>

      {bookingStatus === 'unavailable' && (
        <div className="backend-status-banner flex items-center justify-center gap-[18px] bg-[#fff3cd] px-6 py-2.5 text-[13px] text-[#5f4700] max-sm:items-start max-sm:justify-between max-sm:px-4" role="status">
          <span>Không thể kết nối backend. Dữ liệu sản phẩm và dịch vụ đặt lịch hiện không khả dụng.</span>
          <button type="button" onClick={retry}>Thử kết nối lại</button>
        </div>
      )}

      <div
        ref={menuDialogRef}
        id="mobile-navigation"
        className={`menu-overlay ${menuOpen ? 'is-open' : ''}`}
        aria-hidden={!menuOpen}
        aria-label="Điều hướng di động"
        aria-modal={menuOpen ? 'true' : undefined}
        role="dialog"
        tabIndex={-1}
      >
        <div className="menu-overlay__inner">
          <p className="menu-overlay__intro">Khám phá VinFast</p>
          <nav aria-label="Điều hướng di động">
            {productGroups.map(({ label, to }, index) => (
              <Link
                to={to}
                key={label}
                style={{ '--menu-index': index }}
                tabIndex={menuOpen ? 0 : -1}
              >
                <span>Ô tô · {label}</span>
                <ArrowUpRight size={26} weight="light" />
              </Link>
            ))}
            {links.map((link, index) => (
              <Link
                to={link.to}
                key={link.label}
                style={{ '--menu-index': index + productGroups.length }}
                tabIndex={menuOpen ? 0 : -1}
              >
                <span>{link.label}</span>
                <ArrowUpRight size={26} weight="light" />
              </Link>
            ))}
            <NavLink
              to={bookingHref}
              style={{ '--menu-index': links.length + productGroups.length }}
              tabIndex={menuOpen ? 0 : -1}
            >
              <span>Đặt lịch lái thử</span>
              <ArrowUpRight size={26} weight="light" />
            </NavLink>
          </nav>
          <div className="menu-overlay__foot">
            <span>VinFast Vietnam</span>
            <span>Thuần điện. Thuần Việt.</span>
          </div>
        </div>
      </div>

      {children}
    </div>
  )
}
