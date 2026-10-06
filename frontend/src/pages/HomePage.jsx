/**
 * pages/HomePage.jsx — TRANG CHỦ tại đường dẫn "/". Trang nhiều animation nhất dự án.
 *
 * Dữ liệu: danh sách xe từ useVehicleCatalog(), nội dung biên tập từ usePageContent('home').
 * Xe hero chọn theo content.home.hero.vehicleId; ID sai thì lùi về xe featured đầu tiên,
 * rồi mới tới xe đầu tiên trong catalogue.
 *
 * Thứ tự các mục trên trang (tìm nhanh bằng cách gõ tên class trong ngoặc):
 *  1. Hero + tiêu đề lớn                                  (.home-hero)
 *  2. DẢI THẺ XE — 2 tab Động cơ điện / Dòng xe dịch vụ   (.models-section, id="models")
 *  3. Dải chữ chạy tên các dòng xe                        (.model-marquee)
 *  4. Xe trên đường — ảnh parallax                        (.road-chapter)
 *  5. Video dây chuyền nhà máy                            (.factory-film)
 *  6. Toàn cảnh nhà máy                                   (.factory-origin)
 *  7. CHƯƠNG THƯƠNG HIỆU LẠC HỒNG + góc nhìn canvas      (.lachong-passage)
 *     → code ở components/home/LacHongPassage.jsx, thay khối VF 8 · VF 9 cũ
 *  8. Giới thiệu trợ lý ViVi                              (.vivi-intro)
 *  9. Cảnh editorial Lạc Hồng: text trái, model xe phải       (.drive-out)
 * 10. Hệ sinh thái sở hữu                                 (.ownership-section, id="ecosystem")
 * 11. Câu chuyện công nghệ — cột trái dính khi cuộn       (.technology-story, id="technology")
 * 12. Cảm nhận khách hàng — chỉ hiện khi backend có data  (.voices-section)
 * 13. CTA cuối trang + footer                             (.home-action, .site-footer)
 *
 * Component phụ trong file: VehicleRail (~dòng 30) — dải thẻ xe cuộn ngang, có 2 nút mũi tên,
 * dữ liệu so sánh gọn và 2 lối đi rõ ràng: xem chi tiết hoặc đặt lịch đúng mẫu xe.
 *
 * ẢNH XE LỚN trên trang này là Lạc Hồng — xe trưng bày, CHƯA mở lái thử. Dải thẻ xe ở mục 2
 * vẫn là xe thương mại VF 3–VF 9 và vẫn là cửa vào /booking. Đừng gộp Lạc Hồng vào dải đó.
 *
 * ANIMATION (khối useGSAP ~dòng 124): hero Lạc Hồng đi từ phải sang trái;
 * xe chính diện tiến lại gần khi cuộn (.drive-out__car),
 * parallax ảnh đường/nhà máy. Máy bật prefers-reduced-motion thì hiện thẳng, không animate.
 * LƯU Ý: animation chỉ khởi tạo sau khi catalogue tải xong (`if (cars.length === 0) return`)
 * — nếu không GSAP sẽ đo sai chiều cao trang.
 *
 * Sửa GIAO DIỆN: mục "Home hero", "Product rail", "Pinned technology story", "Voices + action"
 * và "New home visual chapters" trong index.css.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import {
  ArrowLeft,
  ArrowRight,
  BatteryCharging,
  MapPin,
  Play,
  ShieldCheck,
} from '@phosphor-icons/react'
import { AppShell } from '../components/AppShell'
import { IslandButton } from '../components/IslandButton'
import { Reveal } from '../components/Reveal'
import { SmartImage } from '../components/SmartImage'
import { SiteFooter } from '../components/SiteFooter'
import { prefetchVehicle } from '../api/vehicles'
import { carGroups, carImage } from '../data/cars'
import { LacHongPassage } from '../components/home/LacHongPassage'
import { BackToTop } from '../components/BackToTop'
import { FactoryFilmDialog } from '../components/home/FactoryFilmDialog'
import { ViViJourney } from '../components/home/ViViJourney'
import { lacHongEmerge, lacHongHero } from '../data/lachong'
import { usePageContent, useVehicleCatalog, useVehicleColorOptions } from '../hooks/useSiteData'
import {
  factoryAerial,
  factoryFilm,
  roadBanner,
  vf9Sculpture,
} from '../data/media'
import { getClientDeviceProfile } from '../utils/deviceProfile'

gsap.registerPlugin(useGSAP, ScrollTrigger)

const normalizeVehicleFactLabel = (label = '') => String(label)
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/đ/g, 'd')
  .toLowerCase()

const findVehicleFact = (specs = [], pattern) => specs.find(
  ({ label }) => pattern.test(normalizeVehicleFactLabel(label)),
)

// Gợi ý "dải này kéo ngang được": im 2,5 giây không ai đụng thì thẻ xe tự trôi sang trái
// rồi quay về. Chỉ là gợi ý về thao tác, KHÔNG phải carousel tự chạy — nên nó dừng hẳn
// ngay khi người dùng chạm vào, và tối đa 3 lượt.
// Băng chuyền xe chạy vòng tròn. Nhịp cố ý chậm: đây là nền cho người ta liếc
// qua chứ không phải thứ bắt phải nhìn, chạy nhanh là thành quảng cáo nhấp nháy.
// Số lượt lặp danh sách xe để chạy vòng tròn. Bốn là chỗ cân bằng: đủ để điểm
// nhảy nằm xa hẳn vùng đang nhìn, mà chưa nhiều tới mức phình DOM vô ích.
const RAIL_COPIES = 4
const RAIL_SLIDE_DURATION = 0.9
const RAIL_SLIDE_GAP_MS = 3200
const HOME_DETAIL_NAVIGATION_STATE = Object.freeze({ detailOrigin: 'home', detailDepth: 1 })

function VehicleRail({ items, loading, error, onRetry, colorsById }) {
  const rail = useRef(null)
  // Đang tạm dừng vì người dùng rê chuột vào hoặc chạm tay. Giữ trong ref để
  // listener đọc được giá trị mới nhất mà không phải đăng ký lại effect.
  const paused = useRef(false)

  /*
   * VÒNG TRÒN BẰNG CÁCH LẶP DANH SÁCH BỐN LẦN.
   *
   * Nội dung giống hệt nhau lặp lại bốn lượt, nên đi hết đúng MỘT lượt thì trừ
   * lại một lượt vào scrollLeft: chỗ mới rơi vào đúng khung hình y như chỗ cũ,
   * mắt không thấy gì nhảy. Dải trôi mãi không hết, tới VF 9 thì VF 3 nối ngay.
   *
   * VÌ SAO BỐN CHỨ KHÔNG PHẢI HAI: với hai lượt, điểm nhảy nằm ngay giữa dải nên
   * chỉ cần một nhịp lệch là người dùng bắt gặp cú nhảy. Bốn lượt đẩy điểm nhảy
   * ra xa hẳn khỏi vùng đang nhìn, và luôn còn ba lượt nội dung ở bên phải nên
   * kéo tay nhanh cỡ nào cũng không chạm tới mép.
   *
   * Ít hơn ba xe thì không lặp: dải quá ngắn, lặp lên nhìn ra ngay là trùng.
   */
  const loop = items.length > 2 ? Array.from({ length: RAIL_COPIES }, () => items).flat() : items

  // Bề rộng một thẻ cộng khoảng hở, đọc từ DOM thật chứ không đặt cứng: bề rộng
  // thẻ khai bằng minmax(430px, 40vw) nên đổi theo khổ màn hình.
  const stepWidth = (el) => {
    const first = el.firstElementChild
    if (!first) return el.clientWidth * 0.72
    const gap = parseFloat(getComputedStyle(el).columnGap || '0') || 0
    return first.getBoundingClientRect().width + gap
  }

  /*
   * Bề rộng ĐÚNG của một lượt danh sách, đo bằng khoảng cách giữa thẻ đầu của
   * lượt 1 và thẻ đầu của lượt 2.
   *
   * KHÔNG lấy scrollWidth / RAIL_COPIES: scrollWidth còn tính cả đệm hai bên của
   * khung, và lượt cuối không có khoảng hở đuôi, nên phép chia lệch vài pixel.
   * Vài pixel đó cộng dồn qua mỗi vòng và đẩy dải trôi lệch dần.
   */
  const periodWidth = (el) => {
    const first = el.children[0]
    const second = el.children[items.length]
    if (!first || !second) return 0
    return second.offsetLeft - first.offsetLeft
  }

  // Nhảy về đúng chỗ tương ứng ở lượt trước đó. Nội dung ở đó giống hệt nên mắt
  // không thấy gì đổi.
  const wrap = (el) => {
    if (items.length <= 2) return
    const period = periodWidth(el)
    if (period <= 0) return
    if (el.scrollLeft >= period) el.scrollLeft -= period
    // Cuộn ngược lên đầu cũng phải vòng, nếu không dải cụt ở mép trái.
    else if (el.scrollLeft < 1) el.scrollLeft += period
  }

  const slide = (el, direction) => {
    // scroll-behavior:smooth của .vehicle-rail đánh nhau với tween, tắt trong lúc
    // chạy rồi trả lại. (scroll-snap đã bỏ hẳn khỏi CSS, xem ghi chú ở 04-vehicle-rail.css.)
    el.style.scrollBehavior = 'auto'
    // Tween một object trung gian rồi tự gán scrollLeft: với target là DOM element,
    // GSAP đẩy prop lạ sang CSSPlugin và scrollLeft KHÔNG phải thuộc tính CSS.
    const position = { value: el.scrollLeft }
    return gsap.to(position, {
      value: el.scrollLeft + direction * stepWidth(el),
      duration: RAIL_SLIDE_DURATION,
      ease: 'power2.inOut',
      onUpdate: () => {
        el.scrollLeft = position.value
      },
      onComplete: () => {
        wrap(el)
        el.style.scrollBehavior = ''
      },
    })
  }

  const move = (direction) => {
    const el = rail.current
    if (el) slide(el, direction)
  }

  useEffect(() => {
    const el = rail.current
    if (!el || !items.length) return undefined
    // Người tắt hiệu ứng chuyển động thì để dải xe đứng yên, họ tự cuộn.
    if (
      window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 900px), (pointer: coarse)').matches
      || navigator.connection?.saveData === true
    ) return undefined

    let timer
    let tween
    let visible = false

    // Dải vừa đủ chỗ, không kéo được thì chạy tự động là vô nghĩa.
    const canScroll = () => el.scrollWidth - el.clientWidth > 24

    const schedule = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(play, RAIL_SLIDE_GAP_MS)
    }

    const play = () => {
      if (paused.current || !visible || !canScroll()) return
      tween = slide(el, 1)
      tween.eventCallback('onComplete', () => {
        wrap(el)
        el.style.scrollBehavior = ''
        schedule()
      })
    }

    // Rê chuột vào hoặc chạm tay = đang xem: dừng để đọc cho kỹ. Rời ra thì chạy
    // tiếp. KHÔNG tắt vĩnh viễn: bản trước chỉ cần con trỏ lướt ngang qua một lần
    // là hiệu ứng chết luôn, không bao giờ chạy lại.
    const pause = () => {
      paused.current = true
      window.clearTimeout(timer)
      tween?.kill()
      el.style.scrollBehavior = ''
    }

    const resume = () => {
      paused.current = false
      schedule()
    }

    // Kéo tay cũng phải vòng được, nếu không dải cụt ở lượt cuối. Chờ cuộn dừng
    // hẳn mới nhảy, nhảy giữa lúc tay đang kéo là giật.
    let settle
    const onScroll = () => {
      window.clearTimeout(settle)
      settle = window.setTimeout(() => wrap(el), 160)
    }

    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
      if (visible) schedule()
      else window.clearTimeout(timer)
    }, { threshold: 0.35 })
    observer.observe(el)

    el.addEventListener('pointerenter', pause)
    el.addEventListener('pointerleave', resume)
    el.addEventListener('focusin', pause)
    el.addEventListener('focusout', resume)
    el.addEventListener('touchstart', pause, { passive: true })
    el.addEventListener('touchend', resume, { passive: true })
    el.addEventListener('scroll', onScroll, { passive: true })

    return () => {
      window.clearTimeout(timer)
      window.clearTimeout(settle)
      tween?.kill()
      observer.disconnect()
      el.style.scrollBehavior = ''
      el.removeEventListener('pointerenter', pause)
      el.removeEventListener('pointerleave', resume)
      el.removeEventListener('focusin', pause)
      el.removeEventListener('focusout', resume)
      el.removeEventListener('touchstart', pause)
      el.removeEventListener('touchend', resume)
      el.removeEventListener('scroll', onScroll)
    }
  }, [items.length])

  if (loading) {
    return (
      <div className="vehicle-rail vehicle-rail--loading" role="status" aria-live="polite" aria-label="Đang tải danh mục xe">
        {[0, 1].map((index) => (
          <article className="vehicle-tile vehicle-tile--skeleton" key={index} aria-hidden="true">
            <span className="vehicle-skeleton vehicle-skeleton--meta" />
            <span className="vehicle-skeleton vehicle-skeleton--image" />
            <span className="vehicle-skeleton vehicle-skeleton--title" />
            <span className="vehicle-skeleton vehicle-skeleton--facts" />
            <span className="vehicle-skeleton vehicle-skeleton--actions" />
          </article>
        ))}
        <span className="vehicle-loading-label">Đang tải danh mục xe…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="vehicle-empty vehicle-empty--error" role="alert">
        <p>Chưa thể tải danh mục xe.</p>
        <span>Dữ liệu sản phẩm hiện chưa sẵn sàng. Vui lòng thử lại.</span>
        <button type="button" onClick={onRetry}>Thử tải lại</button>
      </div>
    )
  }

  if (!items.length) {
    return (
      <div className="vehicle-empty">
        <p>Chưa có mẫu xe trong nhóm này.</p>
        <span>Bạn hãy chọn nhóm còn lại để xem các mẫu đang mở bán.</span>
      </div>
    )
  }

  return (
    // Khung bao để hai nút điều hướng đứng được hai bên dải, khung phải
    // position:relative thì nút mới neo vào đúng mép trái/phải của dải.
    <div className="vehicle-rail-shell">
      <div className="vehicle-rail" ref={rail}>
        {loop.map((car, position) => {
          // Ba lượt sau chỉ để mắt nhìn cho liền mạch. Máy đọc màn hình và phím
          // Tab phải bỏ qua chúng, nếu không mỗi xe bị đọc và dừng bốn lần.
          const isClone = position >= items.length
          const index = position % items.length
          // id phải kèm vị trí: bản sao dùng lại id của bản gốc là HTML có bốn
          // phần tử trùng id, aria-labelledby trỏ vào đó sẽ vớ nhầm cái đầu tiên.
          const titleId = `vehicle-title-${car.id}-${position}`
          // React 18 chưa hỗ trợ thuộc tính `inert`, nên chặn phím Tab bằng
          // tabIndex. Thiếu bước này thì bấm Tab qua dải xe phải đi bốn vòng.
          const cloneProps = isClone ? { tabIndex: -1 } : null
          const range = car.range || findVehicleFact(car.specs, /quang duong|tam hoat dong|range/)
          const charging = car.charging || findVehicleFact(car.specs, /sac|thoi gian nap|charging/)
          // car.colorOptions về từ GET /vehicles (hiện luôn rỗng); colorsById là phần vá tạm
          // lấy từ GET /vehicles/{id}. Xem TODO trong hooks/useSiteData.js.
          const colors = (car.colorOptions?.length ? car.colorOptions : colorsById[car.id]) || []
          const detailPath = `/models/${encodeURIComponent(car.id)}`
          const categoryLabel = car.category === 'fleet' ? 'Dòng xe dịch vụ' : 'Xe cá nhân'

          return (
            <article
              className="vehicle-tile"
              key={`${car.id}-${position}`}
              aria-hidden={isClone || undefined}
              aria-labelledby={titleId}
              onMouseEnter={() => prefetchVehicle(car.id)}
            >
              {/* CẢ THẺ là một <Link> duy nhất, thay cho mẹo lớp phủ ::after trước đây.
                  Mẹo cũ KHÔNG chạy: ::after nằm trên thẻ <a> trong .vehicle-tile__actions, mà
                  block đó lại `position: relative` — nên `inset: 0` chỉ trùm đúng hàng "Xem chi
                  tiết" cao 48px, bấm vào tên xe hay ảnh xe đều không đi đâu (đã đo bằng
                  document.elementFromPoint). Bọc thẳng thế này thì mọi điểm trong thẻ đều mở
                  trang xe, mà cây accessibility vẫn chỉ có ĐÚNG MỘT link. */}
              <Link
                className="vehicle-tile__core"
                to={detailPath}
                state={HOME_DETAIL_NAVIGATION_STATE}
                aria-label={`Xem chi tiết ${car.name}`}
                onFocus={() => prefetchVehicle(car.id)}
                {...cloneProps}
              >
                <div className="vehicle-tile__meta">
                  <span>{categoryLabel}</span>
                  <span>{car.body || 'Phân khúc đang cập nhật'}</span>
                </div>

                {/* Luôn dùng ảnh studio thật của mẫu xe để dải sản phẩm giữ cùng ngôn ngữ hình ảnh. */}
                <SmartImage
                  className={`vehicle-tile__image vehicle-shot vehicle-shot--${car.studioShot.mode}`}
                  src={car.studioShot.src}
                  alt={`${car.name} - ${car.body || categoryLabel}`}
                  fit={car.studioShot.fit}
                  focalPoint={car.studioShot.focalPoint}
                  aspectRatio={car.studioShot.aspectRatio}
                />

                <div className="vehicle-tile__copy">
                  <h3 id={titleId}>{car.name}</h3>
                  <p>{car.price || 'Giá đang cập nhật'}</p>
                  {car.tagline && <span>{car.tagline}</span>}
                </div>

                <dl className="vehicle-tile__facts">
                  <div>
                    <dt>Chỗ ngồi</dt>
                    <dd>{car.seats || 'Đang cập nhật'}</dd>
                  </div>
                  <div className={!range ? 'is-missing' : ''}>
                    <dt>{range?.label || 'Tầm hoạt động'}</dt>
                    <dd>{range?.value || 'Đang cập nhật'}</dd>
                  </div>
                  <div className={!charging ? 'is-missing' : ''}>
                    <dt>{charging?.label || 'Thông tin sạc'}</dt>
                    <dd>{charging?.value || 'Đang cập nhật'}</dd>
                  </div>
                </dl>

                <div className="vehicle-tile__palette">
                  <span>Màu ngoại thất</span>
                  {colors.length ? (
                    <div className="vehicle-tile__swatches" role="list" aria-label={`Màu ngoại thất ${car.name}`}>
                      {/* Màu backend trả kèm hex thì tô nền; màu lấy từ bảng bổ sung mang ảnh
                          chip chính hãng (sơn kim loại không quy về một hex phẳng được). */}
                      {colors.slice(0, 6).map((color) => (
                        <span
                          className="vehicle-tile__swatch"
                          role="listitem"
                          aria-label={color.name}
                          title={color.name}
                          key={`${car.id}-${color.name}`}
                          style={color.swatch ? undefined : {
                            background: color.secondaryHex
                              ? `linear-gradient(135deg, ${color.hex} 50%, ${color.secondaryHex} 50%)`
                              : color.hex,
                          }}
                        >
                          {color.swatch && <img src={color.swatch} alt="" loading="lazy" />}
                        </span>
                      ))}
                      <small>{colors.length} màu</small>
                    </div>
                  ) : (
                    <small>Đang cập nhật</small>
                  )}
                </div>

                {/* Không còn là <Link> nữa (link đã nằm ở vỏ ngoài) — chỉ là chỉ dấu thị giác,
                    giữ nguyên chữ và mũi tên như cũ để không đổi giao diện. */}
                <div className="vehicle-tile__actions">
                  <span className="vehicle-tile__detail-link">
                    Xem chi tiết <ArrowRight size={17} weight="light" />
                  </span>
                </div>
              </Link>
              <span className="vehicle-tile__index">{String(index + 1).padStart(2, '0')}</span>
            </article>
          )
        })}
      </div>
      <div className="rail-controls" aria-label="Điều khiển danh sách xe">
        <button type="button" onClick={() => move(-1)} aria-label="Xem xe phía trước">
          <ArrowLeft size={20} weight="light" />
        </button>
        <button type="button" onClick={() => move(1)} aria-label="Xem xe tiếp theo">
          <ArrowRight size={20} weight="light" />
        </button>
      </div>
    </div>
  )
}

export function HomePage() {
  const root = useRef(null)
  const factoryVideoRef = useRef(null)
  const location = useLocation()
  const deviceProfile = getClientDeviceProfile()
  const [activeGroup, setActiveGroup] = useState('personal')
  const [storyIndex, setStoryIndex] = useState(0)
  const [factoryDialogOpen, setFactoryDialogOpen] = useState(false)
  const {
    cars,
    loading: carsLoading,
    error: carsError,
    retry: retryCars,
  } = useVehicleCatalog()
  const { data: homeContent } = usePageContent('home')
  const stories = homeContent?.testimonials || []

  const vehicles = useMemo(
    () => cars.filter((car) => car.category === activeGroup),
    [cars, activeGroup],
  )
  // Chỉ hỏi màu cho các xe thuộc tab đang mở, không hỏi cả 14 mẫu.
  const visibleVehicleIds = useMemo(() => vehicles.map((car) => car.id), [vehicles])
  const colorsById = useVehicleColorOptions(visibleVehicleIds)

  useEffect(() => {
    if (location.hash === '#models-service') setActiveGroup('fleet')
    if (location.hash === '#models-electric') setActiveGroup('personal')
  }, [location.hash])

  // Video nằm sâu dưới fold: chỉ chạy khi sắp đi vào viewport và dừng ngay khi rời khỏi.
  // Chế độ tiết kiệm dữ liệu / giảm chuyển động vẫn tải metadata để hiện frame đầu, không autoplay.
  useEffect(() => {
    const video = factoryVideoRef.current
    if (!video) return undefined

    const constrained = getClientDeviceProfile().reducedMotion
      || getClientDeviceProfile().constrained
    if (constrained) return undefined

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) video.play().catch(() => {})
      else video.pause()
    }, { rootMargin: '180px 0px', threshold: 0.08 })
    observer.observe(video)
    return () => {
      observer.disconnect()
      video.pause()
    }
  }, [])

  // Không để video nền tiếp tục chạy phía sau dialog. Khi đóng, chỉ phát lại nếu
  // khối nhà máy vẫn còn trong viewport và thiết bị cho phép chuyển động nền.
  useEffect(() => {
    const video = factoryVideoRef.current
    if (!video) return

    if (factoryDialogOpen) {
      video.pause()
      return
    }

    const profile = getClientDeviceProfile()
    const bounds = video.getBoundingClientRect()
    const visible = bounds.bottom > 0 && bounds.top < window.innerHeight
    if (visible && !profile.reducedMotion && !profile.constrained) video.play().catch(() => {})
  }, [factoryDialogOpen])

  // Hero dùng media local nên phải chạy ngay ở lần paint đầu, không chờ catalogue backend.
  // Tách timeline này khỏi các ScrollTrigger bên dưới để dữ liệu xe về muộn không làm replay.
  useGSAP(
    () => {
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (reduced) {
        gsap.set('[data-hero-reveal]', { opacity: 1, y: 0 })
        gsap.set('.home-hero__car img', { opacity: 1, scale: 1, xPercent: 0, yPercent: 0, filter: 'blur(0px)' })
        gsap.set('.home-hero__line, .home-hero__depth span', { opacity: 1, scaleX: 1 })
        return
      }

      const mobileLite = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches
      if (mobileLite) {
        const heroTimeline = gsap.timeline({ defaults: { ease: 'power3.out' } })
        heroTimeline
          .fromTo(
            '.home-hero__car--lachong img',
            { xPercent: 24, opacity: 0.78 },
            { xPercent: 0, opacity: 1, duration: 0.78 },
          )
          .fromTo(
            '[data-hero-reveal]',
            { y: 18, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.52, stagger: 0.06 },
            0.08,
          )
          .fromTo(
            '.home-hero__line, .home-hero__depth span',
            { scaleX: 0.35, opacity: 0 },
            { scaleX: 1, opacity: 1, duration: 0.55, stagger: 0.04 },
            0.16,
          )
        return () => heroTimeline.kill()
      }

      const heroTimeline = gsap.timeline({ defaults: { ease: 'power4.out' } })
      heroTimeline
        .fromTo(
          '.home-hero__car--lachong img',
          { xPercent: 118, yPercent: 0, scale: 1, opacity: 0.72, filter: 'blur(2px)' },
          { xPercent: 0, yPercent: 0, scale: 1, opacity: 1, filter: 'blur(0px)', duration: 2.35, ease: 'power3.inOut' },
        )
        .fromTo(
          '.home-hero__depth span',
          { scaleX: 0.06, opacity: 0 },
          { scaleX: 1, opacity: 1, duration: 1.7, stagger: 0.12, ease: 'power2.out' },
          0.22,
        )
        .fromTo(
          '.home-hero__line',
          { scaleX: 0.08, opacity: 0 },
          { scaleX: 1, opacity: 1, duration: 1.8, ease: 'power3.out' },
          0.42,
        )
        .fromTo(
          '[data-hero-reveal]',
          { y: 58, opacity: 0, filter: 'blur(10px)' },
          { y: 0, opacity: 1, filter: 'blur(0px)', duration: 0.95, stagger: 0.1 },
          0.28,
        )
    },
    { scope: root },
  )

  // Video reveal phải chạy độc lập với catalogue. Bản trước đặt tween này trong effect
  // chờ `cars.length`, nên khi backend chưa sẵn sàng người dùng chỉ thấy nút xem phim,
  // còn chuyển động phóng 0.5 → 1 hoàn toàn không được khởi tạo.
  useGSAP(
    () => {
      const profile = getClientDeviceProfile()
      const compactPointer = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches
      if (profile.reducedMotion || profile.constrained || compactPointer || navigator.connection?.saveData === true) {
        gsap.set('.factory-film__media', { scale: 1, transformOrigin: 'center center' })
        return
      }

      // Khớp timeline gốc của Antigravity: bắt đầu ở nửa kích thước khi section vừa
      // chạm đáy viewport và đạt kích thước đầy đủ khi mép trên đi tới giữa viewport.
      gsap.fromTo(
        '.factory-film__media',
        { scale: 0.5, transformOrigin: 'center center' },
        {
          scale: 1,
          transformOrigin: 'center center',
          ease: 'power2.out',
          scrollTrigger: {
            trigger: '.factory-film',
            start: 'top bottom',
            end: 'top center',
            scrub: 1,
          },
        },
      )
    },
    { scope: root },
  )

  useGSAP(
    () => {
      // The testing UI has its catalogue synchronously available. In this branch,
      // wait for the API catalogue so GSAP measures the same complete DOM tree.
      if (cars.length === 0) return undefined

      // BACKEND/MEDIA CONTRACT: GSAP owns timing and movement; the API only selects
      // a whitelisted animationPreset and supplies correctly prepared media. Do not
      // send executable animation code or arbitrary selectors from CMS/backend.
      const reducedOrMobile = window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 900px), (pointer: coarse)').matches
      if (reducedOrMobile || navigator.connection?.saveData === true) return

      // Xe tiến từ chiều sâu ra: nhỏ, mờ và nhoè ở xa, rõ dần và lớn dần khi cuộn tới.
      // Chỉ chạm scale/opacity/filter nên trình duyệt không phải tính lại bố cục.
      gsap.fromTo(
        '.drive-out__car',
        { scale: 0.42, opacity: 0, filter: 'blur(5px)', yPercent: 16 },
        {
          scale: 1,
          opacity: 1,
          filter: 'blur(0px)',
          yPercent: 0,
          ease: 'none',
          scrollTrigger: {
            trigger: '.drive-out',
            start: 'top 92%',
            end: 'center 52%',
            scrub: 1,
          },
        },
      )

      // Quầng sáng phía sau nở ra cùng nhịp, tạo cảm giác đèn pha rọi tới.
      gsap.fromTo(
        '.drive-out__aura',
        { scale: 0.55, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          ease: 'none',
          scrollTrigger: { trigger: '.drive-out', start: 'top 92%', end: 'center 52%', scrub: 1 },
        },
      )

      gsap.fromTo(
        '.drive-out__copy',
        { y: 70, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.drive-out',
            start: 'top 78%',
            end: 'center 58%',
            scrub: 0.8,
          },
        },
      )

      gsap.fromTo(
        '.road-chapter__media img',
        { scale: 1.13 },
        {
          scale: 1,
          ease: 'none',
          scrollTrigger: {
            trigger: '.road-chapter',
            start: 'top bottom',
            end: 'bottom top',
            scrub: 1,
          },
        },
      )

      gsap.fromTo(
        '.factory-origin__media',
        { scale: 0.88, opacity: 0.28 },
        {
          scale: 1,
          opacity: 1,
          ease: 'none',
          scrollTrigger: { trigger: '.factory-origin', start: 'top 88%', end: 'center 58%', scrub: 1 },
        },
      )

      // Khối Lạc Hồng tự quản animation của nó trong components/home/LacHongPassage.jsx
      // để bộ xem 360 và phần ảnh nằm chung một scope GSAP.

      gsap.fromTo(
        '.home-action__model',
        { xPercent: -22, opacity: 0 },
        {
          xPercent: 0,
          opacity: 0.8,
          ease: 'none',
          scrollTrigger: { trigger: '.home-action', start: 'top 82%', end: 'center 50%', scrub: 0.9 },
        },
      )

      gsap.utils.toArray('.technology-panel').forEach((panel) => {
        gsap.fromTo(
          panel,
          { opacity: 0.24, scale: 0.88 },
          {
            opacity: 1,
            scale: 1,
            ease: 'none',
            scrollTrigger: {
              trigger: panel,
              start: 'top 88%',
              end: 'center 58%',
              scrub: 1,
            },
          },
        )
      })

      const refreshFrame = window.requestAnimationFrame(() => ScrollTrigger.refresh())

      return () => {
        window.cancelAnimationFrame(refreshFrame)
      }
    },
    { scope: root, dependencies: [cars.length], revertOnUpdate: true },
  )

  const nextStory = (direction) => {
    setStoryIndex((current) => (current + direction + stories.length) % stories.length)
  }

  const selectGroupFromKeyboard = (event, currentIndex) => {
    const lastIndex = carGroups.length - 1
    let nextIndex = currentIndex

    if (event.key === 'ArrowRight') nextIndex = currentIndex === lastIndex ? 0 : currentIndex + 1
    else if (event.key === 'ArrowLeft') nextIndex = currentIndex === 0 ? lastIndex : currentIndex - 1
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = lastIndex
    else return

    event.preventDefault()
    const nextGroup = carGroups[nextIndex]
    setActiveGroup(nextGroup.id)
    window.requestAnimationFrame(() => {
      document.getElementById(nextGroup.id === 'personal' ? 'models-electric' : 'models-service')?.focus()
    })
  }

  const updateFactoryPointer = (event) => {
    if (event.pointerType === 'touch') return
    const bounds = event.currentTarget.getBoundingClientRect()
    event.currentTarget.style.setProperty('--factory-pointer-x', `${event.clientX - bounds.left}px`)
    event.currentTarget.style.setProperty('--factory-pointer-y', `${event.clientY - bounds.top}px`)
  }

  return (
    <AppShell>
      <main ref={root} id="main-content" className="page page--home">
        <section className="home-hero" aria-labelledby="home-title">
          <div className="home-hero__ghost" aria-hidden="true">
            VINFAST
          </div>
          <div className="home-hero__copy">
            <p className="home-hero__kicker" data-hero-reveal>
              VinFast · Mãnh liệt tinh thần Việt Nam
            </p>
            <h1 id="home-title" data-hero-reveal>
              Từ Việt Nam.
              <br />
              Vươn tới tương lai.
            </h1>
            <p className="home-hero__lead" data-hero-reveal>
              VinFast phát triển ô tô điện, công nghệ và hạ tầng sạc tại Việt Nam,
              hướng đến trải nghiệm di chuyển xanh thuận tiện hơn mỗi ngày.
            </p>
            {/* Một hành động chính duy nhất ở hero: xem xe. Nút "Đặt lịch lái thử" từng
                đứng cạnh đây đã bỏ vì header (position:fixed) luôn hiển thị đúng nút đó,
                cùng chữ cùng đích, ngay trong cùng một khung nhìn. */}
            <div className="home-hero__actions" data-hero-reveal>
              <IslandButton to="/#models" variant="dark">
                Khám phá ô tô
              </IslandButton>
            </div>
          </div>
          <div className="home-hero__visual" aria-hidden="true">
            {/* Ảnh xe lớn đầu trang là Lạc Hồng 900 LX (xe trưng bày), không phải xe trong
                catalogue. Hai nút CTA phía trên vẫn dẫn vào dải xe thương mại và /booking. */}
            <div className="home-hero__depth">
              <span /><span /><span /><span />
            </div>
            <SmartImage
              className="home-hero__car home-hero__car--lachong"
              src={lacHongHero.src}
              alt=""
              fit="contain"
              eager
            />
            <span className="home-hero__line" />
          </div>
          <a className="home-hero__scroll" href="#models">
            <span>Cuộn để khám phá</span>
            <span className="home-hero__scroll-line" />
          </a>
        </section>

        <section className="models-section" id="models">
          <div className="section-frame">
            <Reveal className="section-heading section-heading--wide">
              {/* Bỏ nhãn "Ô tô": ngay dưới nó đã là câu "Tìm chiếc VinFast phù hợp
                  với nhu cầu của bạn", nhãn kia không thêm được thông tin nào. */}
              <h2>
                Tìm chiếc VinFast{' '}
                <span
                  className="inline-image inline-image--road"
                  style={{ '--inline-image-url': `url(${carImage('VF8/banner.webp')})` }}
                  aria-hidden="true"
                />{' '}
                phù hợp với nhu cầu của bạn.
              </h2>
            </Reveal>

            <div className="model-tabs" role="tablist" aria-label="Nhóm sản phẩm">
              {carGroups.map((group, index) => (
                <button
                  key={group.id}
                  id={group.id === 'personal' ? 'models-electric' : 'models-service'}
                  type="button"
                  role="tab"
                  aria-selected={activeGroup === group.id}
                  aria-controls="models-panel"
                  tabIndex={activeGroup === group.id ? 0 : -1}
                  onClick={() => setActiveGroup(group.id)}
                  onKeyDown={(event) => selectGroupFromKeyboard(event, index)}
                >
                  <span>{group.label}</span>
                  <small>{group.description}</small>
                </button>
              ))}
            </div>

            <div
              id="models-panel"
              role="tabpanel"
              aria-labelledby={activeGroup === 'personal' ? 'models-electric' : 'models-service'}
              aria-busy={carsLoading}
            >
              <VehicleRail
                items={vehicles}
                loading={carsLoading}
                error={carsError}
                onRetry={retryCars}
                colorsById={colorsById}
              />
            </div>
          </div>
        </section>

        <section className="model-marquee" aria-label="Danh sách dòng xe">
          <div className="model-marquee__track">
            {[...cars, ...cars].map((car, index) => (
              <span key={`${car.id}-${index}`} aria-hidden={index >= cars.length ? 'true' : undefined}>{car.navName}</span>
            ))}
          </div>
        </section>

        <section className="road-chapter" aria-labelledby="road-chapter-title">
          <div className="road-chapter__media">
            <SmartImage src={roadBanner} alt="Hai mẫu ô tô điện VinFast trên cung đường núi" />
          </div>
          <div className="road-chapter__veil" aria-hidden="true" />
          <div className="section-frame road-chapter__copy">
            <p className="eyebrow">Ô tô điện cho từng nhu cầu</p>
            <h2 id="road-chapter-title">Từ phố thị đến những hành trình dài.</h2>
            <Link to="/charging">Khám phá năng lượng cho hành trình <ArrowRight size={18} weight="light" /></Link>
          </div>
        </section>

        {/* TODO [BACKEND/HOME MEDIA]: `factoryFilm` and `factoryAerial` are two
            independent CMS blocks. Do not composite the aerial image into this
            video slot; preserve their separate ordering and focal points. */}
        <section id="factory-film" className="factory-film" aria-labelledby="factory-film-title">
          <div className="factory-film__media" onPointerMove={updateFactoryPointer}>
            {deviceProfile.constrained ? (
              <SmartImage
                className="factory-film__fallback"
                src={factoryAerial}
                alt="Tổ hợp sản xuất VinFast tại Hải Phòng"
                fit="cover"
              />
            ) : (
              <video ref={factoryVideoRef} src={factoryFilm} muted loop playsInline preload="metadata" aria-label="Dây chuyền lắp ráp VinFast" />
            )}
            <div className="factory-film__veil" aria-hidden="true" />
            <div className="factory-film__copy">
              <p>Sản xuất tại Hải Phòng</p>
              <h2 id="factory-film-title">Từng chiếc xe được hoàn thiện qua những công đoạn kiểm soát <em className="no-orphan">chặt chẽ.</em></h2>
              <span>Tổ hợp sản xuất VinFast · Hải Phòng</span>
            </div>
            <button
              className="factory-film__open"
              type="button"
              onClick={() => setFactoryDialogOpen(true)}
              aria-label="Xem đoạn phim về tổ hợp sản xuất VinFast"
              aria-haspopup="dialog"
            />
            <span className="factory-film__watch-pill" aria-hidden="true">
              <span><Play size={17} weight="fill" /></span>
              <strong>Xem câu chuyện</strong>
            </span>
          </div>
        </section>

        <section id="factory-origin" className="factory-origin" aria-labelledby="factory-origin-title">
          <div className="section-frame factory-origin__grid">
            <Reveal className="factory-origin__copy">
              <p className="eyebrow">Tổ hợp sản xuất VinFast</p>
              <h2 id="factory-origin-title">Nơi những chiếc xe VinFast bắt đầu hành trình.</h2>
              <p>
                Tại Hải Phòng, mỗi chiếc xe đi qua các công đoạn sản xuất, lắp ráp và kiểm định trước khi được bàn giao đến khách hàng.
              </p>
            </Reveal>
            <figure className="factory-origin__media">
              <SmartImage src={factoryAerial} alt="Toàn cảnh tổ hợp sản xuất VinFast tại Hải Phòng" />
              <figcaption><span>01</span>Tổ hợp sản xuất VinFast · Hải Phòng</figcaption>
            </figure>
          </div>
        </section>

        <LacHongPassage />

        <ViViJourney />

        {/* Cảnh editorial Lạc Hồng: nội dung và model đứng ở hai vùng riêng biệt. */}
        <section id="drive-out" className="drive-out" aria-label="Xe tiến lại gần theo thao tác cuộn">
          <div className="drive-out__marquee" aria-hidden="true">
            <div>
              <span>Thiết kế tại Việt Nam</span><span>Chế tác cho tương lai</span>
              <span>Thiết kế tại Việt Nam</span><span>Chế tác cho tương lai</span>
            </div>
          </div>
          <div className="section-frame drive-out__layout">
            <div className="drive-out__copy">
              <p className="eyebrow">Thiết kế và chế tác tại Việt Nam</p>
              <h2>Bản sắc Việt<br />trong từng đường nét.</h2>
              <p>
                Qua Lạc Hồng, VinFast thể hiện năng lực phát triển sản phẩm trong nước,
                từ tỷ lệ tổng thể, vật liệu đến những chi tiết nhận diện riêng.
              </p>
              <div className="drive-out__signature"><span>Phát triển</span><strong>Tại Việt Nam</strong></div>
            </div>

            <div className="drive-out__visual">
              <div className="drive-out__aura" aria-hidden="true" />
              <div className="drive-out__lane" aria-hidden="true"><span /><span /><span /></div>
              <SmartImage
                className="drive-out__car"
                src={lacHongEmerge.src}
                alt={lacHongEmerge.alt}
                fit="contain"
              />
            </div>
          </div>
        </section>

        <section className="ownership-section" id="ecosystem">
          <div className="section-frame">
            <Reveal className="section-heading section-heading--split">
              <div>
                <p className="eyebrow">Hệ sinh thái xe điện VinFast</p>
                <h2>Sạc, bảo hành và showroom trong cùng một hành trình.</h2>
              </div>
              <p>
                Tra cứu chính sách, tìm điểm sạc hoặc chọn showroom gần bạn từ những thông tin được trình bày rõ ràng trên cùng website.
              </p>
            </Reveal>

            <div className="ownership-bento">
              <Reveal className="bento-block bento-block--main">
                <Link to="/charging" className="double-bezel double-bezel--dark">
                  <div className="double-bezel__core bento-charge">
                    <SmartImage
                      src={carImage('VF9/cs-home-charger.webp')}
                      alt="Bộ sạc tại nhà VinFast"
                    />
                    <div className="bento-charge__copy">
                      <BatteryCharging size={28} weight="light" />
                      <h3>Chủ động sạc tại nhà.</h3>
                      <p>Tìm hiểu giải pháp sạc tại nhà và mạng lưới trạm sạc cho những hành trình xa hơn.</p>
                    </div>
                  </div>
                </Link>
              </Reveal>

              <Reveal className="bento-block bento-block--support" delay={0.08}>
                <Link to="/after-sales" className="double-bezel">
                  <div className="double-bezel__core bento-support">
                    <ShieldCheck size={28} weight="light" />
                    <div>
                      <h3>Bảo hành dài hạn</h3>
                      <p>Tra cứu chính sách áp dụng cho từng mẫu xe và phiên bản.</p>
                    </div>
                  </div>
                </Link>
              </Reveal>

              <Reveal className="bento-block bento-block--network" delay={0.14}>
                <Link to="/booking" className="double-bezel">
                  <div className="double-bezel__core bento-network">
                    <MapPin size={28} weight="light" />
                    <div>
                      <h3>Showroom gần bạn</h3>
                      <p>Tìm showroom có mẫu xe bạn muốn thử trước khi chọn ngày giờ.</p>
                    </div>
                    <span className="network-pulse" aria-hidden="true" />
                  </div>
                </Link>
              </Reveal>
            </div>
          </div>
        </section>

        <section className="technology-story" id="technology">
          <div className="section-frame technology-story__grid">
            <div className="technology-story__intro">
              <p className="eyebrow">Khám phá trước khi lái thử</p>
              <h2>Hiểu chiếc xe trước khi đến showroom.</h2>
              <p>
                Mỗi trang mẫu xe tập hợp hình ảnh ngoại thất, khoang lái, công nghệ và thông số để bạn xem trước những điểm mình quan tâm.
              </p>
              <IslandButton to="/models/vf8" state={HOME_DETAIL_NAVIGATION_STATE} variant="dark">
                Xem trải nghiệm VF 8
              </IslandButton>
            </div>

            <div className="technology-story__panels">
              {/* Ảnh được chỉ định thẳng theo nội dung của tiêu đề: khoang lái đi với ảnh
                  vô lăng/màn hình, hình khối đi với ảnh ngoại thất, không gian đi với ảnh cabin. */}
              {[
                {
                  id: 'cockpit',
                  car: 'vf8',
                  image: carImage('VF8/ai.webp'),
                  title: 'Khoang lái tập trung',
                  copy: 'Vô lăng, màn hình trung tâm và các phím thao tác nằm gọn trong tầm với của người lái.',
                },
                {
                  id: 'form',
                  car: 'vf7',
                  image: carImage('VF7/vf7-passion.webp'),
                  title: 'Hình khối có chủ đích',
                  copy: 'Ngoại thất cân bằng giữa nhận diện riêng và hiệu quả khí động học.',
                },
                {
                  id: 'cabin',
                  car: 'vf9',
                  image: carImage('VF9/int-slide-4.webp'),
                  title: 'Không gian cho chuyến dài',
                  copy: 'Hàng ghế sau với tựa đầu, màn hình giải trí và tiện nghi dành cho hành khách.',
                },
              ].map((item) => {
                const car = cars.find((entry) => entry.id === item.car)
                if (!car) return null

                return (
                  <article className="technology-panel" key={item.id}>
                    <div className="double-bezel double-bezel--dark">
                      <div className="double-bezel__core">
                        <SmartImage src={item.image} alt={`${car.name} — ${item.title}`} />
                      </div>
                    </div>
                    <div className="technology-panel__caption">
                      <h3>{item.title}</h3>
                      <p>{item.copy}</p>
                    </div>
                  </article>
                )
              })}
            </div>
          </div>
        </section>

        {stories.length > 0 && <section className="voices-section">
          <div className="section-frame voices-section__grid">
            <Reveal className="voices-section__title">
              <p className="eyebrow">Sau một vòng lái</p>
              <h2>Quyết định trở nên rõ ràng hơn.</h2>
            </Reveal>

            <div className="voice-carousel" aria-live="polite">
              <span className="voice-carousel__quote" aria-hidden="true">“</span>
              <blockquote key={storyIndex}>
                <p>{stories[storyIndex].quote}</p>
                <footer>
                  <strong>{stories[storyIndex].name}</strong>
                  <span>{stories[storyIndex].role}</span>
                </footer>
              </blockquote>
              <div className="voice-carousel__controls">
                <span>{String(storyIndex + 1).padStart(2, '0')} / {String(stories.length).padStart(2, '0')}</span>
                <div>
                  <button type="button" onClick={() => nextStory(-1)} aria-label="Câu chuyện trước">
                    <ArrowLeft size={20} weight="light" />
                  </button>
                  <button type="button" onClick={() => nextStory(1)} aria-label="Câu chuyện tiếp theo">
                    <ArrowRight size={20} weight="light" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>}

        {/* TODO [BACKEND/HOME CTA]: This CTA accepts exactly one vehicle render.
            Background is presentation CSS; never return a second car as backdrop. */}
        <section id="home-action" className="home-action">
          <div className="home-action__backdrop" aria-hidden="true" />
          <SmartImage className="home-action__model" src={vf9Sculpture} alt="" aria-hidden="true" />
          <div className="section-frame home-action__content">
            <Reveal>
              <p className="eyebrow">Bắt đầu từ cảm giác sau tay lái</p>
              <h2>Chọn xe. Chọn nơi. Chọn giờ.</h2>
              <p>ViVi sẽ giữ lại toàn bộ lựa chọn để bạn hoàn tất lịch thử xe trong một luồng duy nhất.</p>
              {/* Nút "Hỏi ViVi trước" (to="/agent") đã bỏ: /agent chỉ là Navigate tới
                  /booking trong App.jsx, nên nó bày ra một lựa chọn giả — hai nút cạnh nhau
                  mở ra đúng cùng một trang. Xem lại App.jsx trước khi thêm CTA /agent mới. */}
              <div className="home-action__buttons">
                <IslandButton to="/booking" variant="light">
                  Đặt lịch ngay
                </IslandButton>
              </div>
              {/* Lối vào cho khách QUAY LẠI. Cố ý là link chữ, không phải nút: đặt lịch mới
                  vẫn là hành động chính duy nhất của khối này (xem quy tắc ở Batch 4).
                  `?lookup=1` mở thẳng bước tra cứu, xem BookingPage.jsx. */}
              <p className="home-action__manage">
                Đã đặt lịch rồi? <Link to="/booking?lookup=1">Tra cứu, đổi hoặc huỷ lịch</Link>
              </p>
            </Reveal>
          </div>
        </section>

        <SiteFooter showLearningNotice />
      </main>
      <BackToTop />
      {factoryDialogOpen && (
        <FactoryFilmDialog
          src={factoryFilm}
          poster={factoryAerial}
          onClose={() => setFactoryDialogOpen(false)}
        />
      )}
    </AppShell>
  )
}
