/**
 * pages/CarDetailPage.jsx — TRANG CHI TIẾT XE tại đường dẫn /models/:carId (vd: /models/vf9).
 *
 * Dữ liệu: useVehicleDetail(carId) cho mẫu xe đang xem, useVehicleCatalog() để tìm "xe tiếp theo".
 * ID không có trong catalogue → hiện màn "Không tìm thấy mẫu xe" thay vì trang lỗi.
 *
 * Thứ tự nội dung: Hero → tổng quan → màu → ngoại thất → nội thất → công nghệ
 * → thư viện bổ sung → thông số chi tiết → CTA. Booking dock (góc dưới phải) là lớp
 * nổi, không tham gia vào thứ tự đọc của nội dung chính.
 *
 * ANIMATION (khối useGSAP ~dòng 127) — phần tinh vi nhất dự án:
 * - Xe chạy vào màn hình. Lần đầu xem mẫu này chạy dài (-132%, 1,7 giây), các lần sau
 *   ngắn hơn (-34%, 0,95 giây) — trạng thái ghi trong sessionStorage theo từng mẫu xe.
 * - Chỉ chạy kiểu đó khi backend có `motionImage` (ảnh tách nền). Không có thì xe phóng to dần.
 * - Chữ tuyên ngôn sáng dần từng từ, ảnh từng chương phóng to theo thao tác cuộn.
 * - Mẫu có GLB hợp lệ: model chạy xuyên trái → phải khi sân khấu đã hiện rõ,
 *   sau đó popup thành model xoay/zoom.
 *
 * sessionStorage chỉ còn 1 khoá (cờ giao diện, KHÔNG lưu thông tin cá nhân):
 * vinfast-intro-seen:<id>. Muốn xem lại animation lần đầu: mở tab ẩn danh hoặc xoá khoá này.
 */
import { useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ArrowLeft } from '@phosphor-icons/react'
import { AppShell } from '../components/AppShell'
import { IslandButton } from '../components/IslandButton'
import { Reveal } from '../components/Reveal'
import { SmartImage } from '../components/SmartImage'
import { SiteFooter } from '../components/SiteFooter'
import { Vehicle3DExperience } from '../components/Vehicle3DExperience'
import { VehicleColorConfigurator } from '../components/VehicleColorConfigurator'
import { VehiclePriceVariants } from '../components/VehiclePrice'
import { useVehicleCatalog, useVehicleDetail } from '../hooks/useSiteData'
import { getVehicle3dModel } from '../data/vehicle3d'
import { vehicleGallery } from '../data/vehicle-gallery'
import { limoInteriorFilm } from '../data/media'
import { getClientDeviceProfile } from '../utils/deviceProfile'

gsap.registerPlugin(useGSAP, ScrollTrigger)

/**
 * Thước phim nền, tự chạy và lặp — giống cách vinfast.vn nhúng video sản phẩm.
 *
 * KHÔNG có nút phát/tạm dừng: video không tiếng, tự lặp, chỉ đóng vai trò hình nền chuyển
 * động nên nút điều khiển chỉ làm rối mặt. Máy bật prefers-reduced-motion thì không tự chạy.
 */
function FilmVideo({ className, src, poster, label }) {
  const { constrained, reducedMotion } = getClientDeviceProfile()

  if (constrained) {
    return (
      <SmartImage
        className={`${className || ''} film-video-static`.trim()}
        src={poster}
        alt={label}
        fit="cover"
      />
    )
  }

  return (
    <video
      className={className}
      src={src}
      poster={poster}
      autoPlay={!reducedMotion}
      muted
      loop
      playsInline
      preload="metadata"
      aria-label={label}
    />
  )
}

function ModelFilm({ car }) {
  const film = car.presentationFilm

  if (!film) return null

  return (
    <section id="model-film" className="model-film" aria-labelledby={`model-film-${car.id}`}>
      <div className="model-film__stage">
        <FilmVideo
          className="model-film__video"
          src={film.src}
          poster={film.poster || car.hero}
          label={`Thước phim giới thiệu ${car.name}`}
        />
        <div className="model-film__veil" aria-hidden="true" />
        <div className="model-film__copy" data-film-layer>
          <p>{film.eyebrow}</p>
          <h2 id={`model-film-${car.id}`}>{film.title}</h2>
          <span>{film.copy}</span>
        </div>
      </div>
    </section>
  )
}

const DETAIL_CHAPTER_KEYS = {
  exterior: new Set(['exterior', 'profile', 'rear', 'drive']),
  interior: new Set(['cockpit', 'cabin', 'rearSeats', 'cargo']),
  technology: new Set(['technology', 'charging']),
}

const normalizeDetailLabel = (value = '') => String(value)
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/đ/g, 'd')

const findDetailFact = (facts, expression) => (facts || []).find((fact) => (
  fact?.label && expression.test(normalizeDetailLabel(fact.label))
))

function DetailChapter({ car, chapter }) {
  const title = chapter.title || 'Chi tiết sản phẩm'
  return (
    <article className="detail-chapter">
      <div className={`double-bezel detail-chapter__media ${chapter.tone === 'dark' ? 'double-bezel--dark' : ''}`}>
        <div className={`double-bezel__core detail-chapter__frame is-${chapter.tone || 'dark'}`}>
          <SmartImage
            src={chapter.src}
            alt={`${car.name} — ${chapter.alt || title}`}
            focalPoint={chapter.focalPoint}
            aspectRatio={chapter.aspectRatio}
            fit={chapter.fit}
          />
        </div>
      </div>
      <div className="detail-chapter__copy">
        <h3>{title}</h3>
        {chapter.copy && <p>{chapter.copy}</p>}
      </div>
    </article>
  )
}

/**
 * Một chương nội dung (Ngoại thất / Nội thất / Công nghệ).
 *
 * `hasFeature` = mục này còn nội dung KHÁC ngoài chapters (bộ xem 3D, thước phim…).
 * Không có chapter mà cũng không có feature thì KHÔNG render gì cả.
 *
 * Trước đây mục rỗng vẫn hiện tiêu đề kèm dòng "Chưa có chương hình ảnh… cho <xe>".
 * Đo trên dữ liệu thật 16/08/2026: 13/14 mẫu rơi vào ít nhất một mục rỗng (đa số thiếu
 * "Công nghệ", riêng VF 9 thiếu "Ngoại thất", Nerio Green thiếu cả nội thất lẫn công nghệ)
 * → trang chi tiết nào cũng có ô báo thiếu ảnh, làm cả site trông như hỏng.
 *
 * TODO [BACKEND/CATALOGUE]: gốc rễ là taxonomy chapter của backend lệch. GET /vehicles/{id}
 * chỉ trả 2–3 chapter với `key` không phủ đủ ba nhóm (vd VF 9: charging/cockpit/rearSeats),
 * trong khi `gallery` trả về `sectionKey: null` nên frontend không có căn cứ xếp ảnh vào mục
 * nào. Cần backend trả `sectionKey` cho gallery HOẶC bổ sung chapter cho đủ nhóm. Chừng nào
 * chưa có, các ảnh chưa phân loại vẫn nằm ở mục "Góc nhìn bổ sung" — đúng dữ liệu, không suy đoán.
 */
/**
 * Ảnh sản phẩm bổ sung — trình bày theo đúng cách vinfast.vn làm.
 *
 * Đã đọc CSS bản crawl: toàn bộ quy tắc của họ chỉ là `img { width: 100% }`. Không
 * aspect-ratio, không object-fit, không khung, không đế màu. Ảnh nhận bề rộng của cột và
 * cao tự do theo tỉ lệ gốc, nên người xem thấy TRỌN tấm ảnh, chỉ là nhỏ lại.
 *
 * Hai bản trước em đều sai vì cùng một thói quen: nhét ảnh vào khung có kích thước định sẵn
 * rồi cắt/phóng cho vừa, và bôi đế sáng cho ảnh tách nền. Nay bỏ hết, chỉ còn ảnh.
 * Chiều cao chênh nhau thì để CSS columns xếp khít (xem .detail-gallery trong index.css).
 */
function DetailGalleryStrip({ items, carName }) {
  if (!items.length) return null

  return (
    <div className="detail-gallery" data-count={items.length} aria-label={`Ảnh bổ sung ${carName}`}>
      {items.map((item) => (
        <figure className="detail-gallery__item" key={item.key} data-gallery-item>
          <SmartImage src={item.src} alt={`${carName} — ${item.label}`} />
          <figcaption>{item.label}</figcaption>
        </figure>
      ))}
    </div>
  )
}

function DetailStorySection({ id, eyebrow, title, copy, car, chapters, extraImages = [], hasFeature = false, children }) {
  if (!chapters.length && !extraImages.length && !hasFeature) return null

  return (
    <section
      id={id}
      className={`detail-story-group detail-story-group--${id} ${chapters.length ? '' : 'is-empty'}`.trim()}
      aria-labelledby={`${id}-title`}
    >
      <div className="section-frame detail-story__grid">
        <header className="detail-story__aside">
          <p className="eyebrow">{eyebrow}</p>
          <h2 id={`${id}-title`}>{title}</h2>
          <p>{copy}</p>
        </header>

        {(chapters.length > 0 || extraImages.length > 0) && (
          <div className="detail-story__chapters">
            {chapters.map((chapter, index) => (
              <DetailChapter car={car} chapter={chapter} key={`${chapter.key || id}-${chapter.src}-${index}`} />
            ))}
            <DetailGalleryStrip items={extraImages} carName={car.name} />
          </div>
        )}
      </div>
      <div className="detail-story-group__feature">{children}</div>
    </section>
  )
}

export function CarDetailPage() {
  const { carId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { car, loading, error, retry } = useVehicleDetail(carId)
  const { cars } = useVehicleCatalog()
  const root = useRef(null)
  const detailDepth = Number(location.state?.detailDepth)
  const hasHomeOrigin = location.state?.detailOrigin === 'home'
    && Number.isInteger(detailDepth)
    && detailDepth > 0

  const returnToVehicleSource = () => {
    if (hasHomeOrigin) {
      navigate(-detailDepth)
      return
    }
    navigate('/#models')
  }

  useGSAP(
    () => {
      if (!car) return

      // BACKEND/MEDIA CONTRACT: `motionImage` must follow the cutout requirements
      // documented in BACKEND_HANDOFF.md. The backend may choose a named preset,
      // while duration/easing/selectors stay controlled by this frontend.
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      const mobileLite = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches
        || navigator.connection?.saveData === true
      const visitKey = `vinfast-intro-seen:${car.id}`
      const firstVisit = !window.sessionStorage.getItem(visitKey)
      window.sessionStorage.setItem(visitKey, 'true')

      if (reduced) {
        gsap.set('.detail-hero__car, [data-detail-copy], .model-film__stage, [data-film-layer]', {
          opacity: 1,
          xPercent: 0,
          x: 0,
          y: 0,
          scale: 1,
        })
        gsap.set('.manifesto-word, .detail-chapter__media, .detail-media-grid__item, [data-gallery-item]', {
          opacity: 1,
          scale: 1,
          clearProps: 'transform,filter',
        })
        return
      }

      // Mobile dùng bố cục theo dòng chảy, vì vậy chỉ reveal nhẹ rồi dừng. Không kéo xe
      // thêm 72px theo scroll: chuyển động đó hợp với sân khấu desktop nhưng dễ tạo tràn
      // ngang và va vào vùng chữ khi điện thoại xoay màn hình.
      if (mobileLite) {
        const mobileIntro = gsap.timeline({ defaults: { ease: 'power3.out' } })
        mobileIntro
          .fromTo(
            '.detail-hero__car',
            { opacity: 0.45, scale: 0.96 },
            { opacity: 1, scale: 1, duration: 0.58 },
          )
          .fromTo(
            '[data-detail-copy]',
            { y: 16, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.42, stagger: 0.05 },
            0.08,
          )
        return () => mobileIntro.kill()
      }

      const intro = gsap.timeline({ defaults: { ease: 'power4.out' } })
      const carFrom = car.motionImage
        ? { xPercent: firstVisit ? -132 : -34, opacity: 0, rotate: firstVisit ? -1.2 : 0 }
        : { xPercent: 0, scale: 0.92, opacity: 0 }
      intro
        .fromTo('.detail-hero__car', carFrom, { xPercent: 0, x: 0, scale: 1, opacity: 1, rotate: 0, duration: firstVisit ? 1.7 : 0.95 })
        .fromTo(
          '[data-detail-copy]',
          { y: 48, opacity: 0, filter: 'blur(8px)' },
          { y: 0, opacity: 1, filter: 'blur(0px)', duration: 0.9, stagger: 0.1 },
          '-=0.72',
        )

      gsap.to('.detail-hero__car', {
        x: car.motionImage ? 72 : 0,
        ease: 'none',
        scrollTrigger: {
          trigger: '.detail-hero',
          start: 'top top',
          end: 'bottom top',
          scrub: 1,
        },
      })

      gsap.fromTo(
        '.manifesto-word',
        { opacity: 0.12 },
        {
          opacity: 1,
          stagger: 0.08,
          ease: 'none',
          scrollTrigger: {
            trigger: '.car-manifesto',
            start: 'top 72%',
            end: 'bottom 48%',
            scrub: 1,
          },
        },
      )

      if (car.presentationFilm) {
        const filmTimeline = gsap.timeline({
          scrollTrigger: {
            trigger: '.model-film',
            start: 'top 82%',
            end: 'center 48%',
            scrub: 1,
          },
        })
        filmTimeline
          .fromTo('.model-film__stage', { y: 56, scale: 0.94, opacity: 0.42 }, { y: 0, scale: 1, opacity: 1, ease: 'none' })
          .fromTo('.model-film__video', { scale: 1.07 }, { scale: 1, ease: 'none' }, '<')
          .fromTo('[data-film-layer]', { y: 30, opacity: 0 }, { y: 0, opacity: 1, stagger: 0.06, ease: 'power3.out' }, 0.18)
      }

      gsap.utils.toArray('.detail-chapter__media').forEach((mediaEl) => {
        gsap.fromTo(
          mediaEl,
          { scale: 0.82, opacity: 0.2 },
          {
            scale: 1,
            opacity: 1,
            ease: 'none',
            scrollTrigger: {
              trigger: mediaEl,
              start: 'top 90%',
              end: 'center 62%',
              scrub: 1,
            },
          },
        )
      })

      // Ảnh bổ sung: hiện lên theo hàng, so le nhẹ theo cột để mắt đi ngang chứ không
      // giật cục từng ô. Dùng batch nên mỗi hàng chỉ tạo MỘT ScrollTrigger thay vì một
      // trigger cho mỗi ảnh — trang chi tiết đã có khá nhiều trigger rồi.
      ScrollTrigger.batch('[data-gallery-item]', {
        start: 'top 92%',
        once: true,
        onEnter: (batch) => gsap.fromTo(
          batch,
          { y: 34, opacity: 0, scale: 0.965 },
          { y: 0, opacity: 1, scale: 1, duration: 0.85, stagger: 0.07, ease: 'power3.out', overwrite: true },
        ),
      })

      gsap.utils.toArray('.detail-media-grid__item').forEach((mediaEl) => {
        gsap.fromTo(mediaEl, { scale: 0.9, opacity: 0.35 }, {
          scale: 1,
          opacity: 1,
          ease: 'none',
          scrollTrigger: { trigger: mediaEl, start: 'top 92%', end: 'center 62%', scrub: 0.8 },
        })
      })

    },
    { scope: root, dependencies: [carId, car] },
  )

  if (loading) {
    return (
      <AppShell>
        <main id="main-content" className="detail-state" aria-live="polite" aria-busy="true">
          <div className="detail-state__inner">
            <p className="eyebrow">Catalogue VinFast</p>
            <h1>Đang tải thông tin mẫu xe.</h1>
            <p>Dữ liệu, hình ảnh và bảng màu sẽ xuất hiện ngay khi kết nối hoàn tất.</p>
          </div>
        </main>
      </AppShell>
    )
  }

  if (error && error.status !== 404) {
    return (
      <AppShell>
        <main id="main-content" className="detail-state" role="alert">
          <div className="detail-state__inner">
            <p className="eyebrow">Không thể tải dữ liệu</p>
            <h1>Trang chi tiết đang tạm gián đoạn.</h1>
            <p>Không có thông số hay hình ảnh thay thế được tạo ra trong lúc kết nối lỗi.</p>
            <button type="button" onClick={retry}>Thử tải lại</button>
          </div>
        </main>
      </AppShell>
    )
  }

  if (!car) {
    return (
      <AppShell>
        <main id="main-content" className="not-found">
          <div className="not-found__inner">
            <p className="eyebrow">Không tìm thấy mẫu xe</p>
            <h1>Đường dẫn này chưa có trong catalogue.</h1>
            <p>Hãy quay lại dải sản phẩm để chọn một mẫu xe đang có dữ liệu.</p>
            <IslandButton to="/#models" variant="dark">
              Xem tất cả ô tô
            </IslandButton>
          </div>
        </main>
      </AppShell>
    )
  }

  // TODO [BACKEND/CATALOGUE]: The API must return deterministic sortOrder (or an
  // explicit nextVehicleId) so "Xem mẫu tiếp theo" does not change between requests.
  const nextCar = cars.length
    ? cars[(cars.findIndex((item) => item.id === car.id) + 1) % cars.length]
    : null
  const manifestoText = [car.tagline, car.description].filter(Boolean).join(' ')
  const manifesto = manifestoText.split(' ').filter(Boolean)
  const overviewFacts = [...(car.highlights || []), ...(car.specs || [])]
  const rangeFact = car.range || findDetailFact(overviewFacts, /quang duong|tam hoat dong/)
  const chargingFact = car.charging || findDetailFact(overviewFacts, /sac|thoi gian nap/)
  const overviewItems = [
    {
      label: 'Giá niêm yết',
      value: <VehiclePriceVariants className="vehicle-price-variants" variants={car.priceVariants} fallback={car.price} />,
    },
    { label: 'Sức chứa', value: car.seats },
    { label: rangeFact?.label || 'Tầm hoạt động', value: rangeFact?.value },
    { label: chargingFact?.label || 'Thông tin sạc', value: chargingFact?.value },
  ]
  const chapters = car.chapters || []
  const exteriorChapters = chapters.filter((chapter) => DETAIL_CHAPTER_KEYS.exterior.has(chapter.key || chapter.kind))
  const interiorChapters = chapters.filter((chapter) => DETAIL_CHAPTER_KEYS.interior.has(chapter.key || chapter.kind))
  const technologyChapters = chapters.filter((chapter) => DETAIL_CHAPTER_KEYS.technology.has(chapter.key || chapter.kind))
  const supplementalChapters = chapters.filter((chapter) => !Object.values(DETAIL_CHAPTER_KEYS)
    .some((keys) => keys.has(chapter.key || chapter.kind)))
  const filmSection = ['exterior', 'interior', 'technology'].includes(car.presentationFilm?.sectionKey)
    ? car.presentationFilm.sectionKey
    : null
  // Chỉ vf3 và vf9 có file .glb (xem data/vehicle3d.js) — Vehicle3DExperience trả null cho
  // các mẫu còn lại, nên mục "Ngoại thất" của chúng không được tính là có nội dung.
  const has3dExperience = Boolean(getVehicle3dModel(car.id))
  // Ảnh bổ sung theo mã xe; mẫu nào chưa có thư mục ảnh thì trả về ba mảng rỗng.
  const extraImages = vehicleGallery(car.id)
  // Thanh "đi nhanh tới" chỉ liệt kê mục THỰC SỰ được render, tránh anchor trỏ vào hư không.
  const detailAnchors = [
    { id: 'colors', label: 'Màu sắc', shown: true },
    { id: 'exterior', label: 'Ngoại thất', shown: exteriorChapters.length > 0 || extraImages.exterior.length > 0 || has3dExperience || filmSection === 'exterior' },
    { id: 'interior', label: 'Nội thất', shown: interiorChapters.length > 0 || extraImages.interior.length > 0 || car.id === 'limo-green' || filmSection === 'interior' },
    { id: 'technology', label: 'Công nghệ', shown: technologyChapters.length > 0 || extraImages.technology.length > 0 || filmSection === 'technology' },
    { id: 'specifications', label: 'Thông số', shown: true },
  ].filter((anchor) => anchor.shown)
  const knownMedia = new Set([
    ...chapters.map((chapter) => chapter.src),
    ...(car.colors || []).map((color) => color.image),
  ].filter(Boolean))
  const seenGalleryMedia = new Set()
  const carMedia = (car.media || car.gallery || [])
    .map((asset, index) => {
      const fallbackLabel = `Góc nhìn ${String(index + 1).padStart(2, '0')}`
      if (typeof asset === 'string') return { src: asset, alt: '', label: fallbackLabel, sortOrder: index }
      return {
        src: asset.src || '',
        alt: asset.alt || asset.label || '',
        label: asset.label || fallbackLabel,
        focalPoint: asset.focalPoint,
        aspectRatio: asset.aspectRatio,
        fit: asset.fit,
        sectionKey: asset.sectionKey || null,
        sortOrder: asset.sortOrder ?? index,
      }
    })
    .sort((left, right) => left.sortOrder - right.sortOrder)
    .filter((asset) => {
      if (!asset.src || knownMedia.has(asset.src) || seenGalleryMedia.has(asset.src)) return false
      seenGalleryMedia.add(asset.src)
      return true
    })
  const specificationGroups = car.specificationGroups?.length
    ? car.specificationGroups
    : car.specs?.length
      ? [{ title: 'Thông số chính', items: car.specs }]
      : []
  const brochureTitle = car.brochure && typeof car.brochure === 'object'
    ? car.brochure.title
    : car.brochure
  return (
    <AppShell>
      <main ref={root} id="main-content" className="page page--detail">
        <section className={`detail-hero ${car.name.length > 12 ? 'is-long-name' : ''}`.trim()} aria-labelledby="detail-title">
          <div className="detail-hero__wash" aria-hidden="true" />
          <div className="detail-hero__model-word" aria-hidden="true">{car.name}</div>
          <div className="detail-hero__road" aria-hidden="true"><span /></div>
          <button className="detail-back" type="button" onClick={returnToVehicleSource} data-detail-copy>
            <ArrowLeft size={17} weight="light" />
            Tất cả ô tô
          </button>
          <div className="detail-hero__copy">
            <p data-detail-copy>{car.body}</p>
            <h1 id="detail-title" data-detail-copy>{car.name}</h1>
            <span data-detail-copy>{car.tagline}</span>
          </div>
          <SmartImage
            className={`detail-hero__car ${car.motionImage ? 'is-motion-cutout' : 'is-static-asset'}`}
            src={car.motionImage || car.intro}
            alt={`${car.name} toàn cảnh`}
            eager
          />
          <div className="detail-hero__actions" data-detail-copy>
            <IslandButton to={`/booking?car=${car.id}`} variant="light">
              Đặt lịch lái thử
            </IslandButton>
            <a href="#specifications">Xem thông số</a>
          </div>
        </section>

        {/* Popup gợi ý đặt lịch (.test-drive-nudge) đã gỡ trong đợt dọn CTA: nó hiện ra sau
            2,2 giây ở bottom:94px, tức nằm đè ngay trên .detail-booking-dock ở bottom:22px —
            hai nút xanh cùng chữ "Đặt lịch lái thử", cùng /booking?car=<id>, cách nhau 72px.
            Dock giữ lại vì luôn hiển thị, có kèm tên xe + giá và không cắt ngang người đọc.
            Style .test-drive-nudge trong index.css được giữ nguyên, chưa dùng tới. */}

        <section id="overview" className="detail-overview" aria-labelledby="detail-overview-title">
          <div className="section-frame detail-overview__intro">
            <Reveal className="detail-overview__heading">
              <p className="eyebrow">Tổng quan {car.name}</p>
              <h2 id="detail-overview-title">Những điều cần biết trước khi đi sâu vào từng chi tiết.</h2>
              <p>{car.description || car.tagline}</p>
            </Reveal>

            <dl className="detail-overview__facts" aria-label={`Thông tin tổng quan ${car.name}`}>
              {overviewItems.map((item) => (
                <div className={!item.value ? 'is-missing' : ''} key={item.label}>
                  <dt>{item.label}</dt>
                  <dd>{item.value || 'Đang cập nhật'}</dd>
                </div>
              ))}
            </dl>

            <nav className="detail-overview__anchors" aria-label={`Đi nhanh tới nội dung ${car.name}`}>
              {detailAnchors.map((anchor) => (
                <a href={`#${anchor.id}`} key={anchor.id}>{anchor.label}</a>
              ))}
            </nav>
          </div>

          <div className="car-manifesto">
            <div className="section-frame">
              <p aria-label={manifestoText}>
                {manifesto.map((word, index) => (
                  <span className="manifesto-word" key={`${word}-${index}`} aria-hidden="true">
                    {word}{' '}
                  </span>
                ))}
              </p>
            </div>
          </div>
        </section>

        <VehicleColorConfigurator key={car.id} vehicle={car} />

        <div className="detail-story detail-story--structured" aria-label={`Khám phá ${car.name}`}>
          <DetailStorySection
            id="exterior"
            eyebrow="Ngoại thất"
            title="Nhìn chiếc xe từ hình khối đến chuyển động."
            copy="Tỷ lệ, đường nét và các góc nhìn bên ngoài được gom thành một chương rõ ràng."
            car={car}
            chapters={exteriorChapters}
            extraImages={extraImages.exterior}
            hasFeature={has3dExperience || filmSection === 'exterior'}
          >
            <Vehicle3DExperience car={car} />
            {filmSection === 'exterior' && <ModelFilm car={car} />}
          </DetailStorySection>

          <DetailStorySection
            id="interior"
            eyebrow="Nội thất & không gian"
            title="Từ vị trí người lái đến chỗ ngồi phía sau."
            copy="Khoang lái, không gian hành khách và khả năng sử dụng được đặt cạnh đúng ngữ cảnh của chúng."
            car={car}
            chapters={interiorChapters}
            extraImages={extraImages.interior}
            hasFeature={car.id === 'limo-green' || filmSection === 'interior'}
          >
            {car.id === 'limo-green' && (
              <section className="detail-film" aria-labelledby="detail-film-title">
                <FilmVideo
                  src={limoInteriorFilm}
                  poster={car.hero}
                  label="Thước phim không gian nội thất Limo Green"
                />
                <div className="detail-film__veil" aria-hidden="true" />
                <div className="section-frame detail-film__copy">
                  <p className="eyebrow">Không gian Limo Green</p>
                  <h2 id="detail-film-title">Ba hàng ghế được nhìn trong chuyển động thật.</h2>
                </div>
              </section>
            )}
            {filmSection === 'interior' && <ModelFilm car={car} />}
          </DetailStorySection>

          <DetailStorySection
            id="technology"
            eyebrow="Công nghệ & vận hành"
            title="Thông tin kỹ thuật ở đúng nơi cần tìm."
            copy="Nội dung về cấu trúc, vận hành và sạc chỉ xuất hiện khi có dữ liệu được công bố cho mẫu xe."
            car={car}
            chapters={technologyChapters}
            extraImages={extraImages.technology}
            hasFeature={filmSection === 'technology'}
          >
            {filmSection === 'technology' && <ModelFilm car={car} />}
          </DetailStorySection>

          {supplementalChapters.length > 0 && (
            <DetailStorySection
              id="additional-details"
              eyebrow="Thông tin bổ sung"
              title="Những nội dung chưa được gắn vào một chương cụ thể."
              copy="Phần này giữ nguyên nội dung do nguồn dữ liệu cung cấp, thay vì suy đoán sai ngữ cảnh."
              car={car}
              chapters={supplementalChapters}
            />
          )}
        </div>

        {!filmSection && <ModelFilm car={car} />}

        {carMedia.length > 0 && (
          <section className="detail-media" aria-labelledby="detail-media-title">
            <div className="section-frame">
              <Reveal className="detail-media__heading">
                <p className="eyebrow">Góc nhìn bổ sung</p>
                <h2 id="detail-media-title">Thư viện hình ảnh của {car.name}.</h2>
                <p>{carMedia.length} hình ảnh bổ sung chưa trùng với các chương ở trên.</p>
              </Reveal>
              <div className="detail-media-grid">
                {carMedia.map((asset, index) => (
                  <figure className="detail-media-grid__item" key={`${asset.src}-${index}`}>
                    <SmartImage
                      src={asset.src}
                      alt={asset.alt || `${car.name} · ${asset.label}`}
                      focalPoint={asset.focalPoint}
                      aspectRatio={asset.aspectRatio}
                      fit={asset.fit}
                    />
                  </figure>
                ))}
              </div>
            </div>
          </section>
        )}

        <section className="detail-specs" id="specifications" aria-labelledby="detail-specifications-title">
          <div className="section-frame">
            <Reveal className="detail-specs__heading">
              <p className="eyebrow">Thông số chi tiết</p>
              <h2 id="detail-specifications-title">Dữ liệu quan trọng, không làm bạn phân tâm.</h2>
              <p>{brochureTitle || 'Nguồn brochure đang được cập nhật'}</p>
            </Reveal>

            {specificationGroups.length > 0 ? (
              <div className="detail-specs__groups">
                {specificationGroups.map((group, groupIndex) => (
                  <div className="detail-specs__group" key={`${group.title}-${groupIndex}`}>
                    <h3>{group.title}</h3>
                    <dl className="spec-strip">
                      {group.items.map((spec, index) => (
                        <Reveal className="spec-strip__item" delay={index * 0.05} key={`${spec.label}-${index}`}>
                          <dt>{spec.label}</dt>
                          <dd>{spec.value}</dd>
                        </Reveal>
                      ))}
                    </dl>
                  </div>
                ))}
              </div>
            ) : (
              <div className="detail-specs__empty" role="status">
                <p>Thông số chi tiết của mẫu xe này đang được cập nhật.</p>
              </div>
            )}
          </div>
        </section>

        <section className="detail-action">
          <SmartImage src={car.actionMedia?.src || car.hero} alt="" aria-hidden="true" focalPoint={car.actionMedia?.focalPoint} />
          <div className="detail-action__wash" aria-hidden="true" />
          <div className="section-frame detail-action__content">
            <Reveal>
              <p className="eyebrow">Tiếp theo</p>
              <h2>Cảm nhận {car.name} trên đường thật.</h2>
              <p>Chọn showroom và khung giờ phù hợp, ViVi sẽ giúp bạn giữ lại lựa chọn.</p>
              <div className="detail-action__buttons">
                <IslandButton to={`/booking?car=${car.id}`} variant="light">
                  Đặt lịch lái thử
                </IslandButton>
                {nextCar && (
                  <IslandButton
                    to={`/models/${nextCar.id}`}
                    state={hasHomeOrigin ? { detailOrigin: 'home', detailDepth: detailDepth + 1 } : undefined}
                    variant="ghost-light"
                  >
                    Xem {nextCar.name}
                  </IslandButton>
                )}
              </div>
            </Reveal>
          </div>
        </section>

        <SiteFooter />

        {/* Dock đặt lịch (.detail-booking-dock, góc dưới phải, position:fixed) đã gỡ theo yêu cầu
            16/08/2026: trang này còn 3 lối vào /booking?car=<id> — nút xanh trên header (luôn
            hiển thị, đã mang sẵn mã xe), nút ở hero và CTA cuối trang — nên dock chỉ làm màn hình
            thêm chật. Style .detail-booking-dock trong index.css giữ nguyên, chưa dùng tới. */}
      </main>
    </AppShell>
  )
}
