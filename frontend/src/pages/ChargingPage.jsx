/**
 * pages/ChargingPage.jsx — Trang "Pin & trạm sạc" tại đường dẫn /charging.
 *
 * Trang nội dung thuần. Lấy chargingUnits từ backend (GET /api/v1/content/charging);
 * phần chữ và các mảng số liệu còn lại nằm ngay trong file này.
 *
 * Thứ tự các mục trên trang:
 *  1. Hero "Năng lượng cho mọi điểm đến" — ảnh nền parallax khi cuộn.
 *  2. Thông báo chính sách (charging-notice).
 *  3. Mạng lưới trạm sạc + 6 loại địa điểm  → mảng networkPlaces đầu file.
 *  4. Model 3D trạm sạc tương tác            → ChargingStation3DExperience.
 *  5. Giá điện và phí lưu trụ quá giờ        → mảng overstayFees (miễn phí 10 phút đầu, sau đó tăng dần).
 *  6. Danh mục trụ sạc 250/150/60/30 kW      → dữ liệu TỪ BACKEND (displayedChargingUnits).
 *  7. Sạc tại nhà (bộ sạc treo tường, sạc di động).
 *  8. Quy tắc dùng pin an toàn               → mảng batteryRules.
 *  9. Chính sách thuê pin (khách hàng hiện hữu) + liên hệ + footer.
 *
 * Sửa CHỮ/SỐ LIỆU: 3 mảng networkPlaces / batteryRules / overstayFees nằm ngay đầu file.
 * Sửa ANIMATION: khối useGSAP (~dòng 57) — parallax hero, .charger-card và .network-place trồi lên.
 * Sửa GIAO DIỆN: mục "Ownership chapters" + "Charging-specific editorial surfaces" trong index.css.
 */
import { useRef } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import {
  ArrowDown,
  ArrowUpRight,
  BatteryCharging,
  Buildings,
  Clock,
  Headset,
  Lightning,
  MapPin,
  Plug,
  WarningCircle,
} from '@phosphor-icons/react'
import { AppShell } from '../components/AppShell'
import { ChargingStation3DExperience } from '../components/Vehicle3DExperience'
import { Reveal } from '../components/Reveal'
import { SmartImage } from '../components/SmartImage'
import { chargingUnits as fallbackChargingUnits, ownershipMedia } from '../data/ownership'
import { usePageContent } from '../hooks/useSiteData'
import { getClientDeviceProfile } from '../utils/deviceProfile'

gsap.registerPlugin(useGSAP, ScrollTrigger)

const networkPlaces = [
  'Bãi đỗ xe · bến xe',
  'Trạm dừng nghỉ · trạm xăng dầu',
  'Trung tâm thương mại',
  'Chung cư · tòa văn phòng',
  'Cao tốc · quốc lộ',
  'Địa điểm phù hợp khác',
]

const batteryRules = [
  'Không tự tháo rời, sửa chữa hoặc thay thế bộ phận, dây cáp hay đầu nối điện áp cao.',
  'Chỉ sử dụng nguồn sạc theo khuyến cáo của nhà sản xuất; không dùng pin để vận hành thiết bị khác.',
  'Không tự can thiệp hoặc cập nhật phần mềm trái phép khi chưa có sự cho phép của nhà sản xuất.',
  'Không để xe ở khu vực có thể ngập lụt; tránh nhiệt độ trên 55°C hoặc dưới −20°C liên tục quá 24 giờ.',
  'Sạc ngay khi dung lượng còn dưới 5% và hiển thị màu đỏ trên màn hình.',
]

const overstayFees = [
  { time: 'Phút 01–10', price: 'Miễn phí' },
  { time: 'Phút 11–60', price: '1.000 đ/phút' },
  { time: 'Phút 61–120', price: '2.000 đ/phút' },
  { time: 'Từ phút 121', price: '4.000 đ/phút' },
]

const fallbackChargingUnitByPower = new Map(
  fallbackChargingUnits.map((unit) => [unit.power, unit]),
)

export function ChargingPage() {
  const { data: chargingContent } = usePageContent('charging')
  const contentChargingUnits = chargingContent?.chargingUnits?.length
    ? chargingContent.chargingUnits
    : fallbackChargingUnits
  const displayedChargingUnits = contentChargingUnits.map((unit) => ({
    ...unit,
    // Thông số tiếp tục lấy từ API; product cutout alpha do frontend sở hữu để
    // không phụ thuộc việc media origin đã publish bản PNG mới hay chưa.
    image: fallbackChargingUnitByPower.get(unit.power)?.image || unit.image?.url || unit.image || '',
  }))
  const root = useRef(null)

  useGSAP(
    () => {
      const { compact, constrained, reducedMotion } = getClientDeviceProfile()
      if (reducedMotion || constrained) {
        gsap.set('.ownership-hero__media img, .ownership-hero [data-intro], .charger-card, .network-place, .charger-card__visual img', {
          clearProps: 'transform,filter',
          opacity: 1,
        })
        return undefined
      }

      if (compact) {
        gsap.set('.ownership-hero__media img, .charger-card, .network-place, .charger-card__visual img', {
          clearProps: 'transform,filter',
          opacity: 1,
        })
        const intro = gsap.fromTo(
          '.ownership-hero [data-intro]',
          { y: 18, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.48, stagger: 0.05, ease: 'power3.out' },
        )
        return () => intro.kill()
      }

      gsap.fromTo(
        '.ownership-hero__media img',
        { scale: 1.13 },
        {
          scale: 1,
          ease: 'none',
          scrollTrigger: {
            trigger: '.ownership-hero',
            start: 'top top+=90',
            end: 'bottom top',
            scrub: 1,
          },
        },
      )

      gsap.fromTo(
        '.ownership-hero [data-intro]',
        { y: 56, opacity: 0 },
        { y: 0, opacity: 1, duration: 1, stagger: 0.09, ease: 'power4.out' },
      )

      gsap.utils.toArray('.charger-card, .network-place').forEach((item, index) => {
        gsap.fromTo(
          item,
          { y: 46, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.85,
            delay: Math.min(index * 0.04, 0.16),
            ease: 'power3.out',
            scrollTrigger: { trigger: item, start: 'top 90%', once: true },
          },
        )
      })

      gsap.utils.toArray('.charger-card__visual img').forEach((image) => {
        gsap.fromTo(
          image,
          { scale: 0.84, opacity: 0.38 },
          {
            scale: 1,
            opacity: 1,
            ease: 'none',
            scrollTrigger: {
              trigger: image,
              start: 'top 92%',
              end: 'center 58%',
              scrub: 0.75,
            },
          },
        )
      })

      // Desktop: giữ phần dẫn chuyện đứng yên bằng ScrollTrigger trong khi bốn
      // cấu hình trụ đi qua. Mobile/tablet tiếp tục dùng flow tự nhiên.
      const media = gsap.matchMedia()
      media.add('(min-width: 981px)', () => {
        const intro = root.current?.querySelector('.charger-lineup__intro')
        const cards = root.current?.querySelector('.charger-lineup__cards')
        if (!intro || !cards) return undefined
        const pin = ScrollTrigger.create({
          trigger: cards,
          start: 'top top+=158',
          end: 'bottom bottom-=72',
          pin: intro,
          pinSpacing: false,
          invalidateOnRefresh: true,
        })
        return () => pin.kill()
      })

      return () => media.revert()
    },
    { scope: root },
  )

  return (
    <AppShell>
      <main ref={root} id="main-content" className="page ownership-page ownership-page--charging">
        <section className="ownership-hero ownership-hero--charging" aria-labelledby="charging-title">
          <div className="ownership-hero__media" aria-hidden="true">
            <SmartImage src={ownershipMedia.chargingStationNight} alt="" eager />
          </div>
          <div className="ownership-hero__veil" aria-hidden="true" />
          <div className="section-frame ownership-hero__content">
            <p className="ownership-hero__kicker" data-intro>Pin & trạm sạc</p>
            <h1 id="charging-title" data-intro>
              Năng lượng cho<br />mọi điểm đến.
            </h1>
            <p data-intro>
              Từ quy tắc sử dụng pin đến mạng lưới sạc công cộng và thiết bị tại nhà—mọi thông tin quan trọng nằm trong một hành trình dễ đọc.
            </p>
            <a className="ownership-hero__scroll" href="#charging-network" data-intro>
              Khám phá mạng lưới <ArrowDown size={18} weight="light" />
            </a>
          </div>
        </section>

        <nav className="ownership-subnav" aria-label="Nội dung pin và trạm sạc">
          <div className="section-frame">
            <a href="#charging-notice">Thông báo</a>
            <a href="#charging-network">Mạng lưới</a>
            <a href="#charging-3d">Mô hình 3D</a>
            <a href="#charging-price">Đơn giá</a>
            <a href="#charging-units">Loại trụ</a>
            <a href="#battery-care">Sử dụng pin</a>
          </div>
        </nav>

        <section className="charging-notice" id="charging-notice">
          <div className="section-frame charging-notice__grid">
            <Reveal className="charging-notice__title">
              <WarningCircle size={30} weight="light" aria-hidden="true" />
              <p className="eyebrow">Thông báo dịch vụ</p>
              <h2>Chính sách thuê pin đã chuyển sang giai đoạn duy trì.</h2>
            </Reveal>
            <div className="charging-notice__timeline">
              <article>
                <time dateTime="2025-03-01">01.03.2025</time>
                <p>VinFast dừng cung cấp mới dịch vụ thuê pin cho ô tô điện. Khách hàng đang thuê vẫn có thể tiếp tục theo nhu cầu.</p>
              </article>
              <article>
                <time dateTime="2026-05-01">01.05.2026</time>
                <p>VinFast dừng hỗ trợ chuyển đổi từ thuê sang mua pin, gồm trả thẳng và trả góp. Khách hàng đang trả góp mua pin không bị ảnh hưởng.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="charging-network" id="charging-network">
          <div className="section-frame charging-network__stage">
            <div className="charging-network__image">
              <SmartImage src={ownershipMedia.chargingStationDay} alt="Trạm sạc công cộng VinFast" />
              <div className="charging-network__stats" aria-label="Quy mô mạng lưới">
                <span><strong>63</strong><small>tỉnh thành</small></span>
                <span><strong>150.000+</strong><small>cổng sạc</small></span>
              </div>
            </div>
            <Reveal className="charging-network__copy">
              <p className="eyebrow">Quy hoạch toàn quốc</p>
              <h2>Mỗi điểm dừng đều có thể trở thành điểm nạp năng lượng.</h2>
              <p>
                Thiết bị do VinFast sản xuất và chế tạo, được thiết kế để lắp trong bãi đỗ hiện hữu mà không thay đổi công năng, đồng thời tuân thủ tiêu chuẩn châu Âu về an toàn điện.
              </p>
            </Reveal>
          </div>

          <div className="section-frame network-place-grid">
            {networkPlaces.map((place, index) => (
              <div className="network-place" key={place}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <p>{place}</p>
                {index % 2 === 0 ? <MapPin size={22} weight="light" /> : <Buildings size={22} weight="light" />}
              </div>
            ))}
          </div>
        </section>

        <ChargingStation3DExperience poster={ownershipMedia.chargingStationDay} />

        <section className="charging-price" id="charging-price">
          <div className="section-frame charging-price__grid">
            <Reveal className="charging-price__headline">
              <p className="eyebrow">Chính sách sạc công cộng</p>
              <div className="charging-price__number">
                <strong>3.858</strong>
                <span>VNĐ / kWh</span>
              </div>
              <p>Đơn giá đã gồm VAT, áp dụng từ ngày 19.03.2024 đến khi có thông báo mới.</p>
            </Reveal>

            <div className="charging-price__fees">
              <div className="charging-price__fees-head">
                <Clock size={25} weight="light" aria-hidden="true" />
                <div><strong>Phí lưu trụ sau phiên sạc</strong><small>Tối đa 1.000.000 VNĐ cho một lần</small></div>
              </div>
              {overstayFees.map((fee) => (
                <div className="charging-price__row" key={fee.time}>
                  <span>{fee.time}</span><strong>{fee.price}</strong>
                </div>
              ))}
              <p className="policy-note">Không áp dụng cho xe máy điện và trụ sạc thường ô tô AC 11 kW. Phí sạc và phí lưu trụ của tháng trước được thanh toán trước ngày 15 của tháng tiếp theo.</p>
            </div>
          </div>
        </section>

        <section className="charger-lineup" id="charging-units">
          <div className="section-frame charger-lineup__grid">
            <div className="charger-lineup__intro">
              <p className="eyebrow">Sạc công cộng</p>
              <h2>Bốn mức công suất, cùng một trải nghiệm dễ nhận biết.</h2>
              <p>Từ điểm dừng ngắn trên cao tốc đến bãi đỗ công cộng, mỗi cấu hình được thiết kế theo lưu lượng và thời gian dừng khác nhau.</p>
              {ownershipMedia.chargingBrochure && (
                <a href={ownershipMedia.chargingBrochure} target="_blank" rel="noreferrer">
                  Xem brochure đầy đủ <ArrowUpRight size={18} weight="light" />
                </a>
              )}
            </div>
            <div className="charger-lineup__cards">
              {displayedChargingUnits.map((unit) => (
                <article className="charger-card" key={unit.power}>
                  <div className="charger-card__visual">
                    <SmartImage src={unit.image} alt={`Trụ ${unit.name} ${unit.power} VinFast`} />
                  </div>
                  <div className="charger-card__copy">
                    <div><small>{unit.name}</small><strong>{unit.power}</strong></div>
                    <ul>{unit.facts.map((fact) => <li key={fact}>{fact}</li>)}</ul>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="home-charging">
          <div className="section-frame">
            <Reveal className="section-heading section-heading--wide">
              <p className="eyebrow">Sạc tại nhà & theo xe</p>
              <h2>Chủ động nạp năng lượng tại nơi chiếc xe nghỉ.</h2>
            </Reveal>
            <div className="home-charging__grid">
              <article className="home-charger home-charger--main">
                <div className="home-charger__media">
                  <SmartImage src={ownershipMedia.wallCharger} alt="Bộ sạc treo tường VinFast AC 7,4 kW" />
                </div>
                <div>
                  <Plug size={28} weight="light" aria-hidden="true" />
                  <span>Bộ sạc treo tường</span>
                  <h3>AC 7,4 kW</h3>
                  <p>Sạc có dây AC mức 2 · 1 pha 230 VAC ±10% · một đầu ra · bảo vệ quá áp, thấp áp, dòng rò, quá nhiệt, mất nối đất và chống cháy.</p>
                </div>
              </article>
              <article className="home-charger">
                <div className="home-charger__media home-charger__media--pair">
                  <SmartImage src={ownershipMedia.portableCharger} alt="Thiết bị sạc di động VinFast" />
                  <SmartImage src={ownershipMedia.portableChargerAlt} alt="Bộ cáp sạc di động theo xe VinFast" />
                </div>
                <div>
                  <BatteryCharging size={28} weight="light" aria-hidden="true" />
                  <span>Thiết bị theo xe</span>
                  <h3>Sạc di động</h3>
                  <p>Giải pháp linh hoạt khi cần dùng nguồn điện phù hợp. VinFast khuyến cáo dùng thiết bị chính hãng để hạn chế nguy cơ về điện và cháy nổ.</p>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="battery-care" id="battery-care">
          <div className="section-frame battery-care__grid">
            <Reveal className="battery-care__visual">
              <SmartImage src={ownershipMedia.availableIndicator} alt="Đèn báo trụ sạc VinFast khả dụng" />
              <div><Lightning size={34} weight="light" /><span>Trụ sáng xanh</span><strong>Sẵn sàng sạc</strong></div>
            </Reveal>
            <div className="battery-care__content">
              <p className="eyebrow">Quy định sử dụng pin</p>
              <h2>Năm nguyên tắc để bảo vệ hệ thống điện áp cao.</h2>
              <div className="battery-care__rules">
                {batteryRules.map((rule, index) => (
                  <details key={rule} open={index === 0}>
                    <summary><span>0{index + 1}</span>{rule}</summary>
                    <p>Liên hệ xưởng dịch vụ VinFast nếu xe hiển thị cảnh báo hoặc có dấu hiệu bất thường; không tự can thiệp vào hệ thống.</p>
                  </details>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="legacy-rental">
          <div className="section-frame legacy-rental__grid">
            <Reveal>
              <p className="eyebrow">Dành cho khách hàng đang thuê pin</p>
              <h2>Thông tin duy trì hợp đồng hiện hữu.</h2>
              <p>Không phải ưu đãi mở mới. Nội dung dưới đây chỉ giúp khách hàng đang sử dụng dịch vụ kiểm tra chu kỳ và nghĩa vụ thanh toán.</p>
            </Reveal>
            <div className="legacy-rental__facts">
              <article><span>Chu kỳ cước</span><strong>26 → 25</strong><p>Từ ngày 26 tháng trước đến ngày 25 tháng hiện tại; chốt ODO lúc 22:00 ngày 25.</p></article>
              <article><span>Thời hạn</span><strong>Không giới hạn</strong><p>Duy trì đến khi hết nhu cầu. Khi chuyển nhượng xe, chủ mới ký xác nhận tiếp tục hợp đồng.</p></article>
              <article><span>Đổi gói</span><strong>4.120.000 VNĐ</strong><p>Mỗi lần, đã gồm VAT.</p></article>
              <article><span>Thanh toán chậm</span><strong>10% / năm</strong><p>Áp dụng cho phí thuê pin và phí đền bù pin hỏng quá hạn, nếu có.</p></article>
            </div>
            <p className="legacy-rental__payment">Chi phí thuê pin được thanh toán trả sau, trước ngày 15 của tháng tiếp theo: trực tiếp tại điểm cung cấp dịch vụ bằng phương thức được chấp nhận hoặc trực tuyến qua ứng dụng VinFast.</p>
          </div>
        </section>

        <section className="ownership-contact ownership-contact--charging">
          <div className="section-frame ownership-contact__grid">
            <div>
              <BatteryCharging size={42} weight="light" aria-hidden="true" />
              <p className="eyebrow">Tư vấn trạm & thiết bị sạc</p>
              <h2>Một cuộc gọi trước khi cắm sạc.</h2>
            </div>
            <div className="ownership-contact__actions">
              <a href="tel:1900232389"><Headset size={24} weight="light" /><span><small>Hotline · nhánh 5</small><strong>1900 23 23 89</strong></span></a>
              <a href="#charging-units"><Plug size={24} weight="light" /><span><small>Danh mục thiết bị</small><strong>Xem lại loại trụ</strong></span></a>
            </div>
          </div>
        </section>

        <footer className="ownership-footer">
          <div className="section-frame">
            <strong>VINFAST</strong>
            <p>Đơn giá và chính sách được hệ thống lại từ brochure do người dùng cung cấp; có thể được VinFast cập nhật. Luôn đối chiếu tài liệu hiệu lực trước khi giao dịch.</p>
          </div>
        </footer>
      </main>
    </AppShell>
  )
}
