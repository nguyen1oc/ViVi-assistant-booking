/**
 * components/booking/VehicleWorkspace.jsx — MẪU XE trong luồng đặt lịch.
 *
 * - VehicleShot: ảnh studio của xe
 * - VehicleSwitcher: hộp thoại đổi/chọn mẫu xe lái thử
 * - VehiclePanel: thẻ "Mẫu xe đang giữ" ở workspace bên trái
 */
import { useEffect, useState } from 'react'
import { ArrowRight, CaretDown, Check, X } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'
import { SmartImage } from '../SmartImage'
import { BookingSuccessVehicleModel } from '../Vehicle3DExperience'
import { getVehicle3dModel } from '../../data/vehicle3d'
import { carGroups } from '../../data/cars'
import { useDialogFocus } from '../../hooks/useDialogFocus'
import { VehiclePriceVariants } from '../VehiclePrice'

export function VehicleShot({ car, className = '', eager = false, mode = car.studioShot.mode }) {
  return (
    <SmartImage
      className={`vehicle-shot vehicle-shot--${mode} ${className}`.trim()}
      src={car.studioShot.src}
      alt={`${car.name} — ảnh studio`}
      eager={eager}
    />
  )
}

export function VehicleSwitcher({ cars, currentId, onSelect, onClose }) {
  const dialogRef = useDialogFocus({ onClose })

  return (
    <div
      ref={dialogRef}
      className="vehicle-switcher"
      role="dialog"
      aria-modal="true"
      aria-labelledby="vehicle-switcher-title"
      tabIndex={-1}
      onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}
    >
      <div className="vehicle-switcher__panel">
        <button type="button" className="vehicle-switcher__close" onClick={onClose} aria-label="Đóng bảng chọn xe">
          <X size={17} weight="light" />
        </button>
        <header>
          <p>Đổi mẫu xe lái thử</p>
          <h2 id="vehicle-switcher-title">Bạn muốn cầm lái mẫu nào?</h2>
          <small>ViVi giữ lại địa chỉ và showroom bạn đã chọn; chỉ khung giờ được mở lại để ghép đúng xe mới.</small>
        </header>
        <div className="vehicle-switcher__body">
          {carGroups.map((group) => (
            <section key={group.id}>
              <div className="vehicle-switcher__group">
                <strong>{group.label}</strong>
                <small>{group.description}</small>
              </div>
              <div className="vehicle-switcher__grid">
                {cars.filter((car) => car.category === group.id).map((car) => {
                  const active = car.id === currentId
                  return (
                    <button
                      type="button"
                      key={car.id}
                      className={active ? 'is-active' : ''}
                      onClick={() => onSelect(car)}
                      aria-pressed={active}
                    >
                      <VehicleShot car={car} className="vehicle-switcher__shot" />
                      <span className="vehicle-switcher__meta">
                        <strong>{car.name}</strong>
                        <small>{car.body} · {car.seats}</small>
                      </span>
                      <span className="vehicle-switcher__state">
                        {active
                          ? <><Check size={13} weight="bold" /> Đang chọn</>
                          : <>Chọn mẫu này <ArrowRight size={13} weight="light" /></>}
                      </span>
                    </button>
                  )
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}

export function VehiclePanel({ car }) {
  // Mẫu nào có file .glb đã duyệt (hiện là VF 3 và VF 9) thì màn hình trái hiện MODEL 3D xoay
  // được, thay cho ảnh tĩnh — kể cả khi mới chọn xe chứ không đợi tới màn đặt xong. Các mẫu
  // còn lại chưa có model nên vẫn giữ nguyên ảnh studio.
  const hasApproved3dModel = Boolean(getVehicle3dModel(car.id))
  const [infoOpen, setInfoOpen] = useState(false)
  const extraSpecs = car.specs.slice(3)

  return (
    <section
      className={`studio-vehicle ${hasApproved3dModel ? 'has-booking-model' : ''} ${infoOpen ? 'has-details' : ''}`.replace(/\s+/g, ' ').trim()}
      aria-label={`Mẫu xe ${car.name}`}
    >
      <div className="studio-vehicle__ambient" aria-hidden="true" />
      <div className="studio-vehicle__heading">
        <span>Mẫu xe đang giữ</span>
        <strong>{car.name}</strong>
        <small>{car.body} · {car.seats}</small>
      </div>
      <div className="studio-vehicle__stage" key={car.id}>
        {hasApproved3dModel
          ? <BookingSuccessVehicleModel car={car} className="studio-vehicle__image" />
          : <VehicleShot car={car} className="studio-vehicle__image" eager />}
      </div>
      <div className="studio-vehicle__specs">
        {car.specs.slice(0, 3).map((spec) => (
          <div key={spec.label}><strong>{spec.value}</strong><span>{spec.label}</span></div>
        ))}
      </div>
      <button
        type="button"
        className="studio-vehicle__more"
        aria-expanded={infoOpen}
        onClick={() => setInfoOpen((open) => !open)}
      >
        {infoOpen ? 'Thu gọn thông tin xe' : 'Xem lại thông tin xe'}
        <CaretDown size={15} weight="light" style={{ transform: infoOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.35s var(--ease-heavy)' }} />
      </button>

      {infoOpen && (
        <div className="studio-vehicle__details">
          {car.tagline && <p className="studio-vehicle__tagline">{car.tagline}</p>}
          <dl>
            <div>
              <dt>Giá niêm yết</dt>
              <dd><VehiclePriceVariants className="vehicle-price-variants" variants={car.priceVariants} fallback={car.price} /></dd>
            </div>
            <div><dt>Kiểu xe</dt><dd>{car.body || 'Đang cập nhật'}</dd></div>
            {extraSpecs.map((spec) => (
              <div key={spec.label}><dt>{spec.label}</dt><dd>{spec.value}</dd></div>
            ))}
          </dl>
          {!extraSpecs.length && (
            <small>Thông số chi tiết hơn của mẫu xe này đang được cập nhật.</small>
          )}
        </div>
      )}
    </section>
  )
}
