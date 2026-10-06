/**
 * components/booking/BookingUpsell.jsx — Khối mời chọn xe ở đầu khung chat ViVi.
 *
 * Thay cho hàng 4 nút chữ "VF 3 · VF 5 · VF 6 · VF 7" trước đây. Bốn nút đó dàn đều nhau nên
 * không nói được showroom đang muốn đẩy mẫu nào, và chỉ có chữ nên khách phải tự nhớ mặt xe.
 *
 * Nay còn ĐÚNG 2 mẫu, do sale admin chọn (xem api/upsell.js). Mỗi mẫu là một thẻ có ảnh xe,
 * tên, kiểu dáng, số chỗ và giá. Có ảnh vì đây là lúc khách chưa xem xe nào, mặt xe là thứ
 * quyết định họ bấm hay không. Ảnh cố ý để nhỏ và nằm ngang cạnh phần chữ, không dựng thẻ
 * cao như trang chủ, để khối này không lấn ô nhập tin nhắn ngay bên dưới.
 *
 * Khách bấm một thẻ là đi tiếp đúng luồng cũ qua onChoose (chooseCar ở BookingPage), và khối
 * này tự biến mất vì allowedActions không còn 'choose_vehicle'. Ai không thích cả hai mẫu thì
 * dùng dòng "Xem tất cả N mẫu" ở chân khối để mở bảng chọn xe đầy đủ.
 */
import { ArrowRight, CarProfile } from '@phosphor-icons/react'
import { VehicleShot } from './VehicleWorkspace'
import { upsellThumb } from '../../media/assets'

const DEFAULT_HEADLINE = 'Hãy chọn mẫu xe ưa thích của bạn'

/**
 * Backend trả giá dạng "Giá niêm yết · 299.000.000 VNĐ". Thẻ ở đây chỉ rộng khoảng 195px khi
 * màn chat co lại, để nguyên chuỗi đó thì đúng phần khách cần đọc là con số lại bị cắt mất,
 * chỉ còn trơ mấy chữ "Giá niêm yế…". Bỏ nhãn phía trước, giữ lại vế cuối.
 * Mẫu thương mại không có số (ví dụ "Chính sách dành cho kinh doanh") thì giữ nguyên.
 */
const shortPrice = (price = '') => {
  const parts = String(price).split('·')
  return parts[parts.length - 1].trim()
}

export function BookingUpsell({ cars, onChoose, onBrowseAll, totalCount = 0, headline = '', note = '' }) {
  if (!cars.length) return null

  return (
    <section className="booking-upsell" aria-label="Mẫu xe showroom đang giới thiệu">
      <div className="booking-upsell__head">
        <strong>{headline || DEFAULT_HEADLINE}</strong>
        {note && <small>{note}</small>}
      </div>

      <div className="booking-upsell__grid">
        {cars.map((car) => (
          <button type="button" key={car.id} className="booking-upsell__card" onClick={() => onChoose(car)}>
            {/* Ưu tiên bản ảnh đã chuẩn hoá để ba chiếc xe đứng chung một đường bánh; mẫu nào
                chưa có bản chuẩn hoá thì vẫn dùng ảnh studio như cũ chứ không bỏ trống. */}
            <span className="booking-upsell__shot">
              {upsellThumb(car.id)
                ? <img className="booking-upsell__image" src={upsellThumb(car.id)} alt="" aria-hidden="true" loading="lazy" />
                : <VehicleShot car={car} className="booking-upsell__image" />}
            </span>
            <span className="booking-upsell__meta">
              <strong>{car.name}</strong>
              <small>{[car.body, car.seats].filter(Boolean).join(' · ')}</small>
              {car.price && <em>{car.priceFrom || shortPrice(car.price)}</em>}
            </span>
            <ArrowRight size={14} weight="light" className="booking-upsell__go" aria-hidden="true" />
          </button>
        ))}
      </div>

      {onBrowseAll && totalCount > 0 && (
        <button type="button" className="booking-upsell__browse" onClick={onBrowseAll} aria-haspopup="dialog">
          <CarProfile size={14} weight="light" aria-hidden="true" />
          Xem tất cả {totalCount} mẫu
        </button>
      )}
    </section>
  )
}
