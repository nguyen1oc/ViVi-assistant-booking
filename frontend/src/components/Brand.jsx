/**
 * components/Brand.jsx — Logo VinFast ở góc trái header, bấm vào là về ĐẦU trang chủ.
 *
 * Dùng ở: AppShell.jsx (mọi trang marketing) và BookingPage.jsx (header riêng của trang đặt lịch).
 * Prop `inverse`: bật khi header nằm trên nền tối, thêm class .brand--inverse để đảo màu logo.
 *
 * Ảnh logo lấy từ src/media/local/vehicle-media/. CSS dùng object-fit: contain nên logo
 * luôn hiện trọn khung, không bị cắt hay kéo méo. Style ở mục "Floating navigation" trong index.css.
 *
 * Hai hành vi KHÁC NHAU, đừng gộp:
 * - Đang ở trang khác  → điều hướng bình thường về "/", RouteEffects đưa lên đầu trang.
 * - Đang ở chính trang chủ → <Link> không đổi location nên RouteEffects không chạy và
 *   trước đây bấm logo không có gì xảy ra. Nay chặn điều hướng và tự cuộn lên đầu.
 *   Đây là chỗ khác với nút Back của trình duyệt: Back phục hồi đúng vị trí cũ, còn
 *   logo thì luôn về đầu trang.
 */
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { vehicleImage } from '../media/assets'
import { scrollPageToTop } from '../utils/scrollToTop'

const vinfastLogo = vehicleImage('Vinfast-logo-new_NO_Tagline -2D-Horizontal black.png')

// Dùng trực tiếp logo ngang do chủ dự án cung cấp để đồng nhất nhận diện giữa
// website và ViVi. `object-fit: contain` trong CSS giữ nguyên toàn bộ chi tiết logo.
export function Brand({ inverse = false }) {
  const location = useLocation()
  const navigate = useNavigate()

  const handleClick = (event) => {
    if (location.pathname !== '/') return
    // Nhường lại cho trình duyệt các kiểu bấm mở tab mới / cửa sổ mới.
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return

    event.preventDefault()

    // Còn #anchor trên URL thì phải bỏ đi, không thì thanh địa chỉ vẫn trỏ tới một mục
    // giữa trang trong khi màn hình đã ở đầu. replace để không đẻ thêm một entry lịch sử.
    if (location.hash) navigate('/', { replace: true })
    scrollPageToTop()
  }

  return (
    <Link
      to="/"
      className={`brand ${inverse ? 'brand--inverse' : ''}`}
      aria-label="VinFast - về đầu trang chủ"
      onClick={handleClick}
    >
      <img className="brand__logo" src={vinfastLogo} alt="" aria-hidden="true" />
    </Link>
  )
}
