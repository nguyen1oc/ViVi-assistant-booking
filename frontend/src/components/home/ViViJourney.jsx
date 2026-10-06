import { useState } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  CalendarBlank,
  CarProfile,
  Check,
  CheckCircle,
  ChatCircleText,
  Clock,
  EnvelopeSimple,
  MapPin,
  MapPinLine,
  NavigationArrow,
} from '@phosphor-icons/react'
import { SmartImage } from '../SmartImage'
import { carImage } from '../../data/cars'
import { viviAvatar, viviPortrait } from '../../data/media'
import { commonMedia } from '../../media/assets'
import { ViViParticleField } from './ViViParticleField'

const VF9_JOURNEY_IMAGE = carImage('VF9/CE1W-cutout.webp')

const JOURNEY_STEPS = [
  {
    id: 'request',
    shortLabel: 'Nhu cầu',
    icon: ChatCircleText,
    eyebrow: 'Bước 1 · Bắt đầu bằng một câu',
    title: 'Bạn nói điều mình đang cần.',
    copy: 'Không cần điền một biểu mẫu dài. Hãy cho ViVi biết mẫu xe, khu vực hoặc thời gian bạn muốn lái thử.',
  },
  {
    id: 'vehicle',
    shortLabel: 'Mẫu xe',
    icon: CarProfile,
    eyebrow: 'Bước 2 · Xác định chiếc xe',
    title: 'ViVi giữ đúng mẫu xe bạn chọn.',
    copy: 'Thông tin mẫu xe được giữ xuyên suốt hành trình để khi tìm showroom và lịch trống, bạn không phải chọn lại từ đầu.',
  },
  {
    id: 'showroom',
    shortLabel: 'Showroom',
    icon: MapPinLine,
    eyebrow: 'Bước 3 · Tìm nơi phù hợp',
    title: 'Chỉ xem những showroom có xe.',
    copy: 'ViVi ưu tiên nơi có đúng mẫu xe và lịch lái thử, sau đó sắp xếp theo khoảng cách từ vị trí bạn cung cấp.',
  },
  {
    id: 'slot',
    shortLabel: 'Khung giờ',
    icon: CalendarBlank,
    eyebrow: 'Bước 4 · Hoàn tất lựa chọn',
    title: 'Chọn một giờ thuận tiện.',
    copy: 'Ngày, giờ, mẫu xe và showroom được gom trong một bản tóm tắt để bạn kiểm tra trước khi tạo lịch.',
  },
  {
    id: 'confirmation',
    shortLabel: 'Xác nhận',
    icon: EnvelopeSimple,
    eyebrow: 'Bước 5 · Mang lịch hẹn theo bạn',
    title: 'Email và phiếu lịch được cá nhân hoá.',
    copy: 'Sau khi xác nhận, bạn nhận được mã lịch, thời gian, showroom và thông tin tư vấn viên trong email cùng phiếu lịch để tra cứu lại bất cứ lúc nào.',
  },
]

function ViViIllustration({ children, label }) {
  return (
    <div className="vivi-journey__illustration">
      <div className="vivi-journey__illustration-label">{label}</div>
      {children}
    </div>
  )
}

function RequestPreview() {
  return (
    <ViViIllustration label="Cuộc trò chuyện">
      <div className="vivi-journey__chat">
        <p className="vivi-journey__bubble vivi-journey__bubble--user">
          Tôi muốn lái thử VF 9 gần Quận 7 vào cuối tuần.
        </p>
        <div className="vivi-journey__assistant-row">
          <span className="vivi-journey__mini-avatar"><img src={viviAvatar} alt="" /></span>
          <p className="vivi-journey__bubble vivi-journey__bubble--assistant">
            Được rồi. Mình sẽ tìm showroom có VF 9 và lịch phù hợp cho bạn.
          </p>
        </div>
      </div>
      <div className="vivi-journey__composer"><span>Nhắn cho ViVi</span><ArrowRight size={17} weight="light" /></div>
    </ViViIllustration>
  )
}

function VehiclePreview() {
  return (
    <ViViIllustration label="Mẫu xe đã chọn">
      <div className="vivi-journey__vehicle-card">
        <div className="vivi-journey__vehicle-copy">
          <small>SUV điện cao cấp</small>
          <strong>VF 9</strong>
          <span><CheckCircle size={17} weight="fill" /> Đã giữ cho lịch này</span>
        </div>
        <SmartImage src={VF9_JOURNEY_IMAGE} alt="" fit="contain" />
      </div>
      <div className="vivi-journey__facts">
        <span><strong>7</strong><small>chỗ ngồi</small></span>
        <span><strong>SUV</strong><small>thuần điện</small></span>
        <span><strong>VF 9</strong><small>mẫu đang chọn</small></span>
      </div>
    </ViViIllustration>
  )
}

function ShowroomPreview() {
  return (
    <ViViIllustration label="Showroom phù hợp">
      <div className="vivi-journey__showroom-layout">
        <div className="vivi-journey__showroom-list">
          <strong>3 showroom có VF 9</strong>
          <small>Ưu tiên theo khoảng cách</small>
          {[
            ['01', 'VinFast Quận 7', '2,4 km'],
            ['02', 'VinFast Thảo Điền', '6,8 km'],
            ['03', 'VinFast Landmark 81', '8,1 km'],
          ].map(([rank, name, distance], index) => (
            <div className={index === 0 ? 'is-active' : ''} key={name}>
              <span>{rank}</span><p><strong>{name}</strong><small>Còn lịch lái thử</small></p><em>{distance}</em>
            </div>
          ))}
        </div>
        <div className="vivi-journey__map">
          <span className="vivi-journey__route vivi-journey__route--one" />
          <span className="vivi-journey__route vivi-journey__route--two" />
          <span className="vivi-journey__map-pin vivi-journey__map-pin--one"><MapPin size={18} weight="fill" /></span>
          <span className="vivi-journey__map-pin vivi-journey__map-pin--two"><MapPin size={16} weight="fill" /></span>
          <span className="vivi-journey__map-pin vivi-journey__map-pin--three"><MapPin size={16} weight="fill" /></span>
          <span className="vivi-journey__location"><NavigationArrow size={15} weight="fill" /></span>
        </div>
      </div>
    </ViViIllustration>
  )
}

function SlotPreview() {
  return (
    <ViViIllustration label="Ngày và giờ lái thử">
      <div className="vivi-journey__date-row">
        <span><small>Th 6</small><strong>28</strong></span>
        <span className="is-active"><small>Th 7</small><strong>29</strong></span>
        <span><small>CN</small><strong>30</strong></span>
        <span><small>Th 2</small><strong>31</strong></span>
      </div>
      <div className="vivi-journey__time-grid">
        {['09:00', '10:30', '13:30', '15:00'].map((time) => (
          <span className={time === '10:30' ? 'is-active' : ''} key={time}>{time}</span>
        ))}
      </div>
      <div className="vivi-journey__summary">
        <span><Check size={18} weight="bold" /></span>
        <p><strong>VF 9 · 10:30, Thứ Bảy</strong><small>VinFast Quận 7</small></p>
        <Clock size={20} weight="light" />
      </div>
    </ViViIllustration>
  )
}

/* Bước 5 dựng lại đúng hai thứ khách nhận được sau khi đặt lịch, không bịa thêm:
 * - Thư xác nhận: bản rút gọn của render_booking_confirmation_email()
 *   (backend/src/services/booking/email_templates.py, xem bản dựng ở
 *   resources/mockups/email-xac-nhan.html) — nền #121212, vạch vàng #F5C542 mang tên
 *   khách, khối "ViVi gửi bạn thông tin lịch hẹn" viền vàng, nhãn vàng in hoa.
 * - Thiệp mời: bản rút gọn của .invitation-card ở InvitationPreviewPage.
 * Hai thẻ nằm cạnh nhau trong một lưới, KHÔNG chồng lên nhau như bản trước. */
function ConfirmationPreview() {
  return (
    <ViViIllustration label="Thư xác nhận và thiệp mời đã gửi">
      <div className="vivi-journey__confirmation">
        <article className="vivi-journey__email">
          <header>
            <span><img src={commonMedia.vinfastLogo} alt="" /><strong>VINFAST</strong></span>
            <small>Thư xác nhận</small>
          </header>

          <p className="vivi-journey__email-headline">Phiếu xác nhận<br />lịch hẹn</p>
          <p className="vivi-journey__email-name">Nguyễn Hoàng Minh</p>

          <p className="vivi-journey__email-lede">
            Lịch hẹn lái thử <em>VinFast VF 9</em> của bạn đã được đặt thành công.
          </p>

          <div className="vivi-journey__email-panel">
            <strong>ViVi gửi bạn<br />thông tin lịch hẹn</strong>
            <dl>
              <div><dt>Mã lịch hẹn</dt><dd>VF260829A47C3D</dd></div>
              <div><dt>Thời gian hẹn</dt><dd>10:30 · Thứ Bảy, 29/08</dd></div>
              <div><dt>VinFast Quận 7</dt><dd>1058 Nguyễn Văn Linh, Quận 7</dd></div>
              <div><dt>Tư vấn viên</dt><dd>Trần Minh Khoa · 0938 xxx 219</dd></div>
            </dl>
          </div>

          <span className="vivi-journey__email-cta">Kiểm tra thông tin lịch của bạn</span>
        </article>

        <article className="vivi-journey__invite">
          <header>
            <small>VinFast trân trọng mời</small>
            <strong>Thiệp mời lái thử</strong>
          </header>

          <div className="vivi-journey__invite-vehicle">
            <span aria-hidden="true">VF 9</span>
            <SmartImage src={VF9_JOURNEY_IMAGE} alt="" fit="contain" />
          </div>

          <div className="vivi-journey__invite-card">
            <div className="vivi-journey__invite-when">
              <p><small>Thời gian</small><strong>10:30</strong></p>
              <p><small>Ngày hẹn</small><strong>Thứ Bảy</strong><b>29.08.2026</b></p>
            </div>
            <div className="vivi-journey__invite-where">
              <MapPin size={17} weight="light" />
              <p><small>Điểm hẹn</small><strong>VinFast Quận 7</strong></p>
            </div>
            <div className="vivi-journey__invite-code">
              <small>Mã lịch hẹn</small><strong>VF260829A47C3D</strong>
            </div>
          </div>
        </article>
      </div>
    </ViViIllustration>
  )
}

function JourneyPreview({ stepId }) {
  if (stepId === 'vehicle') return <VehiclePreview />
  if (stepId === 'showroom') return <ShowroomPreview />
  if (stepId === 'slot') return <SlotPreview />
  if (stepId === 'confirmation') return <ConfirmationPreview />
  return <RequestPreview />
}

export function ViViJourney() {
  const [activeIndex, setActiveIndex] = useState(0)
  const activeStep = JOURNEY_STEPS[activeIndex]

  const selectFromKeyboard = (event, currentIndex) => {
    let nextIndex = currentIndex
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') nextIndex = (currentIndex + 1) % JOURNEY_STEPS.length
    else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') nextIndex = (currentIndex - 1 + JOURNEY_STEPS.length) % JOURNEY_STEPS.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = JOURNEY_STEPS.length - 1
    else return

    event.preventDefault()
    setActiveIndex(nextIndex)
    window.requestAnimationFrame(() => document.getElementById(`vivi-journey-tab-${nextIndex}`)?.focus())
  }

  const move = (direction) => {
    setActiveIndex((current) => (current + direction + JOURNEY_STEPS.length) % JOURNEY_STEPS.length)
  }

  return (
    <section className="vivi-journey" id="vivi" aria-labelledby="vivi-journey-title">
      <div className="section-frame">
        <div className="vivi-journey__heading">
          <div>
            <p className="eyebrow">ViVi đặt lịch</p>
            <h2 id="vivi-journey-title">Từ một nhu cầu đến lịch lái thử rõ ràng.</h2>
          </div>
          <div className="vivi-journey__intro">
            <p>
              ViVi giữ lại mẫu xe, vị trí và thời gian bạn đã chọn. Sau khi hoàn tất, email và phiếu lịch cá nhân hoá giúp bạn mang đầy đủ thông tin tới buổi lái thử.
            </p>
          </div>
        </div>

        <div className="vivi-journey__stage">
          <ViViParticleField />

          <div className="vivi-journey__media" aria-hidden="true">
            <img className="vivi-journey__mascot" src={viviPortrait} alt="" />
            <div className="vivi-journey__visual" key={activeStep.id}>
              <JourneyPreview stepId={activeStep.id} />
            </div>
            <span className="vivi-journey__media-note">Minh hoạ quy trình đặt lịch</span>
          </div>

          <div className="vivi-journey__story">
            <div className="vivi-journey__tabs" role="tablist" aria-label="Các bước đặt lịch cùng ViVi">
              {JOURNEY_STEPS.map((step, index) => {
                const selected = index === activeIndex
                const Icon = step.icon
                return (
                  <button
                    id={`vivi-journey-tab-${index}`}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    aria-controls="vivi-journey-panel"
                    tabIndex={selected ? 0 : -1}
                    className={selected ? 'is-active' : ''}
                    onClick={() => setActiveIndex(index)}
                    onKeyDown={(event) => selectFromKeyboard(event, index)}
                    key={step.id}
                  >
                    <span className="vivi-journey__step-number" aria-hidden="true">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className="vivi-journey__step-icon" aria-hidden="true">
                      <Icon size={22} weight="light" />
                    </span>
                    <strong>{step.shortLabel}</strong>
                  </button>
                )
              })}
            </div>

            <div
              id="vivi-journey-panel"
              className="vivi-journey__panel"
              role="tabpanel"
              aria-labelledby={`vivi-journey-tab-${activeIndex}`}
              aria-live="polite"
              key={`copy-${activeStep.id}`}
            >
              <p>{activeStep.eyebrow}</p>
              <h3>{activeStep.title}</h3>
              <span>{activeStep.copy}</span>
            </div>

            <div className="vivi-journey__controls">
              <span><strong>{String(activeIndex + 1).padStart(2, '0')}</strong> / {String(JOURNEY_STEPS.length).padStart(2, '0')}</span>
              <div>
                <button type="button" onClick={() => move(-1)} aria-label="Xem bước trước"><ArrowLeft size={20} weight="light" /></button>
                <button type="button" onClick={() => move(1)} aria-label="Xem bước tiếp theo"><ArrowRight size={20} weight="light" /></button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
