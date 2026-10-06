import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import { ArrowCounterClockwise, House, MapPin } from '@phosphor-icons/react'
import gsap from 'gsap'
import { Link, useLocation, useParams } from 'react-router-dom'
import { apiGet } from '../api/client'
import { useDialogFocus } from '../hooks/useDialogFocus'
import { modelImage, showcaseImage, vehicleImage } from '../media/assets'
import { vehicleMediaMap } from '../media/vehicle-media-map'

const vinfastWordmark = vehicleImage('Vinfast-logo-new_NO_Tagline -2D-Horizontal black.png')
const lacHongSide = showcaseImage('lac-hong-900lx/film-side.png')
const VINFAST_HOME_URL = 'https://c3-app-053.pages.dev/'

const SAMPLE_INVITATION = {
  guestName: 'Nguyễn Hoàng Minh',
  time: '09:30',
  weekday: 'Thứ Sáu',
  date: '28.08.2026',
  vehicleId: 'vf9',
  model: 'VinFast VF 9 Plus',
  showroom: 'VinFast Landmark 81',
  address: '208 Nguyễn Hữu Cảnh, Phường Thạnh Mỹ Tây, TP.HCM',
  bookingCode: 'VF260828A47C3D',
}

const cleanParam = (params, key, fallback, maxLength = 90) => {
  const value = params.get(key)?.trim().replace(/\s+/g, ' ')
  return value ? value.slice(0, maxLength) : fallback
}

const invitationFromSearch = (search) => {
  const params = new URLSearchParams(search)
  const requestedVehicleId = params.get('model')?.trim().toLowerCase()
  const vehicleId = requestedVehicleId && vehicleMediaMap[requestedVehicleId]
    ? requestedVehicleId
    : SAMPLE_INVITATION.vehicleId
  const defaultModelName = vehicleId === SAMPLE_INVITATION.vehicleId
    ? SAMPLE_INVITATION.model
    : `VinFast ${vehicleMediaMap[vehicleId].name}`

  return {
    guestName: cleanParam(params, 'name', SAMPLE_INVITATION.guestName, 60),
    time: cleanParam(params, 'time', SAMPLE_INVITATION.time, 8),
    weekday: cleanParam(params, 'weekday', SAMPLE_INVITATION.weekday, 20),
    date: cleanParam(params, 'date', SAMPLE_INVITATION.date, 16),
    vehicleId,
    model: cleanParam(params, 'modelName', defaultModelName, 60),
    showroom: cleanParam(params, 'showroom', SAMPLE_INVITATION.showroom, 80),
    address: cleanParam(params, 'address', SAMPLE_INVITATION.address, 140),
    bookingCode: cleanParam(params, 'code', SAMPLE_INVITATION.bookingCode, 32),
  }
}

export function InvitationPreviewPage() {
  const location = useLocation()
  const invitation = useMemo(() => invitationFromSearch(location.search), [location.search])
  return <InvitationExperience invitation={invitation} />
}

const invitationFromApi = (payload) => {
  const start = new Date(payload.start_at)
  if (Number.isNaN(start.getTime())) throw new Error('INVALID_INVITATION_DATE')
  const vehicleId = vehicleMediaMap[payload.vehicle_id]
    ? payload.vehicle_id
    : SAMPLE_INVITATION.vehicleId
  const dateParts = new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'Asia/Ho_Chi_Minh',
  }).formatToParts(start)
  const dateValue = Object.fromEntries(dateParts.map((part) => [part.type, part.value]))

  return {
    guestName: payload.guest_name || 'Khách hàng VinFast',
    time: new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
      timeZone: 'Asia/Ho_Chi_Minh',
    }).format(start),
    weekday: new Intl.DateTimeFormat('vi-VN', {
      weekday: 'long',
      timeZone: 'Asia/Ho_Chi_Minh',
    }).format(start),
    date: `${dateValue.day}.${dateValue.month}.${dateValue.year}`,
    vehicleId,
    model: payload.model || `VinFast ${vehicleMediaMap[vehicleId].name}`,
    showroom: payload.showroom || 'Showroom VinFast',
    address: payload.address || '',
    bookingCode: payload.booking_code || '',
  }
}

export function InvitationPage() {
  const { token = '' } = useParams()
  const [state, setState] = useState({ status: 'loading', invitation: null })

  useEffect(() => {
    const controller = new AbortController()
    setState({ status: 'loading', invitation: null })
    apiGet(`/invitations/${encodeURIComponent(token)}`, {
      signal: controller.signal,
      cacheKey: `public-invitation:${token}`,
      fallbackToCache: false,
    })
      .then((payload) => setState({ status: 'ready', invitation: invitationFromApi(payload) }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ status: 'error', invitation: null })
      })
    return () => controller.abort()
  }, [token])

  if (state.status === 'loading') {
    return (
      <main className="invitation-state" aria-live="polite">
        <div className="invitation-state__loader" />
        <p>Đang chuẩn bị thiệp mời của bạn</p>
      </main>
    )
  }

  if (state.status === 'error') {
    return (
      <main className="invitation-state invitation-state--error">
        <span>Thiệp mời VinFast</span>
        <h1>Không thể mở thiệp mời này.</h1>
        <p>Liên kết không hợp lệ hoặc lịch hẹn không còn hiệu lực.</p>
        <Link to="/">Về trang chủ</Link>
      </main>
    )
  }

  return <InvitationExperience invitation={state.invitation} />
}

function InvitationExperience({ invitation }) {
  const root = useRef(null)
  const intro = useRef(null)
  const content = useRef(null)
  const timeline = useRef(null)
  const [assetReady, setAssetReady] = useState(false)
  const [introDone, setIntroDone] = useState(false)
  const selectedVehicleImage = modelImage(invitation.vehicleId)

  useEffect(() => {
    const previousTitle = document.title
    document.title = `Thiệp mời lái thử | ${invitation.guestName}`
    return () => { document.title = previousTitle }
  }, [invitation.guestName])

  useEffect(() => {
    let active = true
    const image = new Image()
    const ready = () => { if (active) setAssetReady(true) }
    image.onload = ready
    image.onerror = ready
    image.src = lacHongSide
    const timeout = window.setTimeout(ready, 3000)
    return () => {
      active = false
      window.clearTimeout(timeout)
    }
  }, [])

  useEffect(() => {
    document.body.classList.toggle('invitation-film-open', !introDone)
    return () => document.body.classList.remove('invitation-film-open')
  }, [introDone])

  const finishIntro = useCallback((animate = true) => {
    timeline.current?.kill()
    if (!intro.current || !content.current) {
      setIntroDone(true)
      return
    }

    gsap.set(content.current, { opacity: 1, y: 0 })
    if (!animate) {
      gsap.set(intro.current, { autoAlpha: 0 })
      setIntroDone(true)
      return
    }

    gsap.to(intro.current, {
      autoAlpha: 0,
      duration: 0.28,
      ease: 'power2.out',
      onComplete: () => setIntroDone(true),
    })
  }, [])

  const introDialogRef = useDialogFocus({ active: !introDone, onClose: () => finishIntro(true) })
  const setIntroNode = useCallback((node) => {
    intro.current = node
    introDialogRef.current = node
  }, [introDialogRef])

  useGSAP(() => {
    if (introDone || !intro.current || !content.current) return undefined

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reducedMotion) {
      finishIntro(false)
      return undefined
    }
    if (!assetReady) return undefined

    const mobileLite = window.matchMedia('(max-width: 720px), (pointer: coarse)').matches
      || navigator.connection?.saveData === true
    const brand = intro.current.querySelector('.invitation-film__brand')
    const brandRule = intro.current.querySelector('.invitation-film__brand-rule')
    const vehicle = intro.current.querySelector('.invitation-film__vehicle')
    const streaks = intro.current.querySelectorAll('.invitation-film__streak')
    const message = intro.current.querySelector('.invitation-film__message')
    const messageRule = intro.current.querySelector('.invitation-film__message-rule')
    // Animate the visual wrapper instead of the image itself. Keeping a transform on a
    // transparent WebP makes Safari/Retina reuse a softened GPU texture after the intro.
    const selectedVehicle = content.current.querySelector('.invitation-vehicle__visual')
    const vehicleWidth = vehicle.getBoundingClientRect().width || window.innerWidth
    const travel = ((window.innerWidth + vehicleWidth) / 2) + (mobileLite ? 36 : 80)
    const centerPauseX = mobileLite ? -8 : -24

    gsap.set(content.current, { opacity: 0, y: mobileLite ? 12 : 24 })
    gsap.set(brand, { opacity: 0, scale: 0.95 })
    gsap.set(brandRule, { scaleX: 0, transformOrigin: 'center' })
    gsap.set(vehicle, { x: -travel, scale: mobileLite ? 0.92 : 0.78, opacity: 1 })
    gsap.set(streaks, { scaleX: 0, opacity: 0, transformOrigin: 'right center' })
    gsap.set(message, { opacity: 0, y: 14 })
    gsap.set(messageRule, { scaleX: 0, transformOrigin: 'center' })
    gsap.set(selectedVehicle, { opacity: 0, x: mobileLite ? 22 : 54, scale: 0.96 })

    const sequence = gsap.timeline({
      defaults: { ease: 'power3.inOut' },
      onComplete: () => {
        // Return the vehicle to normal browser compositing once the motion is finished,
        // so fine bodywork and transparent edges are rendered at the device's full DPR.
        gsap.set(selectedVehicle, { clearProps: 'transform,opacity' })
        setIntroDone(true)
      },
    })

    sequence
      .to(brand, { opacity: 1, scale: 1, duration: mobileLite ? 0.42 : 0.62, ease: 'power3.out' })
      .to(brandRule, { scaleX: 1, duration: 0.42, ease: 'power3.out' }, '<+0.1')
      .to({}, { duration: mobileLite ? 0.26 : 0.5 })
      .to(brand, { opacity: 0, scale: 0.98, duration: 0.3, ease: 'power2.in' })
      .addLabel('drive')
      .to(streaks, { scaleX: 1, opacity: 0.34, duration: 0.72, stagger: 0.05, ease: 'power2.out' }, 'drive')
      .to(vehicle, {
        x: centerPauseX,
        scale: mobileLite ? 0.96 : 0.84,
        duration: mobileLite ? 1.35 : 1.75,
        ease: 'power2.out',
      }, 'drive+=0.02')
      .to(vehicle, {
        x: travel,
        scale: mobileLite ? 1 : 0.88,
        duration: mobileLite ? 1.2 : 1.55,
        ease: 'power2.in',
      })
      .to(streaks, { scaleX: 0.2, opacity: 0, duration: 0.58, stagger: 0.04, ease: 'power2.in' }, '<+0.5')
      .to(message, { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }, '>-0.08')
      .to(messageRule, { scaleX: 1, duration: 0.44, ease: 'power3.out' }, '<+0.1')
      .to({}, { duration: mobileLite ? 0.48 : 0.72 })
      .to(content.current, { opacity: 1, y: 0, duration: 0.72, ease: 'power3.out' })
      .to(selectedVehicle, { opacity: 1, x: 0, scale: 1, duration: 0.82, ease: 'power3.out' }, '<+0.08')
      .to(intro.current, { autoAlpha: 0, duration: 0.54, ease: 'power2.inOut' }, '<')

    timeline.current = sequence
    return () => sequence.kill()
  }, { scope: root, dependencies: [assetReady, introDone], revertOnUpdate: true })

  const replay = () => {
    window.scrollTo({ top: 0, behavior: 'instant' })
    setIntroDone(false)
  }

  return (
    <div ref={root} className="invitation-preview">
      {!introDone && (
        <section ref={setIntroNode} className="invitation-film" role="dialog" aria-modal="true" aria-label="Phim mở đầu thiệp mời" tabIndex={-1}>
          <button className="invitation-film__skip" type="button" onClick={() => finishIntro(true)}>
            Bỏ qua
          </button>

          <div className="invitation-film__brand" aria-hidden="true">
            <img src={vinfastWordmark} alt="" />
            <span className="invitation-film__brand-rule" />
          </div>

          <div className="invitation-film__road" aria-hidden="true">
            <span className="invitation-film__streak" />
            <span className="invitation-film__streak" />
            <span className="invitation-film__streak" />
            <img className="invitation-film__vehicle" src={lacHongSide} alt="" />
          </div>

          <div className="invitation-film__message" aria-hidden="true">
            <span className="invitation-film__message-rule" />
            <p>Lời mời dành riêng cho</p>
            <strong>{invitation.guestName}</strong>
          </div>
        </section>
      )}

      <div ref={content} className={`invitation-preview__content${introDone ? ' is-ready' : ''}`} aria-hidden={!introDone} inert={!introDone ? '' : undefined}>
        <header className="invitation-header">
          <a
            className="invitation-header__home"
            href={VINFAST_HOME_URL}
            aria-label="Đến trang chủ VinFast"
          >
            <House size={18} weight="light" aria-hidden="true" />
            <span>Trang chủ</span>
          </a>
          <img className="invitation-header__logo" src={vinfastWordmark} alt="VinFast" />
          <button className="invitation-header__replay" type="button" onClick={replay}>
            <ArrowCounterClockwise size={18} weight="light" aria-hidden="true" />
            <span>Xem lại</span>
          </button>
        </header>

        <main className="invitation-main">
          <section className="invitation-title" aria-labelledby="invitation-heading">
            <p>VinFast trân trọng mời</p>
            <h1 id="invitation-heading">Thiệp mời lái thử</h1>
            <div className="invitation-guest">
              <span aria-hidden="true" />
              <strong>{invitation.guestName}</strong>
            </div>
          </section>

          <section className="invitation-vehicle" aria-label={`Mẫu xe đã chọn: ${invitation.model}`}>
            <strong className="invitation-vehicle__model" aria-hidden="true">
              {vehicleMediaMap[invitation.vehicleId]?.name || invitation.model}
            </strong>
            <div className="invitation-vehicle__visual">
              <img
                className="invitation-vehicle__image"
                src={selectedVehicleImage}
                alt={invitation.model}
                decoding="async"
                fetchPriority="high"
                draggable="false"
              />
            </div>
            <div className="invitation-vehicle__caption">
              <span>Mẫu xe bạn đã chọn</span>
              <strong>{invitation.model}</strong>
            </div>
          </section>

          <article className="invitation-card">
            <div className="invitation-card__intro">
              <h2>Thông tin lịch hẹn</h2>
            </div>

            <div className="invitation-card__schedule">
              <div className="invitation-card__time">
                <span>Thời gian</span>
                <strong>{invitation.time}</strong>
              </div>
              <div className="invitation-card__date">
                <span>Ngày hẹn</span>
                <strong>{invitation.weekday}</strong>
                <b>{invitation.date}</b>
              </div>
            </div>

            <div className="invitation-card__showroom">
              <MapPin size={23} weight="light" aria-hidden="true" />
              <div>
                <span>Điểm hẹn</span>
                <h3>{invitation.showroom}</h3>
                <p>{invitation.address}</p>
              </div>
            </div>

            <dl className="invitation-card__meta">
              <div>
                <dt>Mã lịch hẹn</dt>
                <dd>{invitation.bookingCode}</dd>
              </div>
            </dl>
          </article>

          <p className="invitation-note">
            Vui lòng có mặt trước giờ hẹn 10 phút. Đội ngũ VinFast sẽ chuẩn bị xe và đón tiếp bạn tại showroom.
          </p>

          <footer className="invitation-footer">
            <span />
            <p>Hẹn gặp bạn tại VinFast</p>
            <span />
          </footer>
        </main>
      </div>
    </div>
  )
}
