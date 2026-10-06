/**
 * Sân khấu GLB dùng chung.
 *
 * - Vehicle3DExperience: cinematic chạy xuyên màn hình rồi mở model tương tác
 *   trong trang chi tiết của mọi mẫu có GLB web hợp lệ.
 * - BookingSuccessCinematic: che tối màn hình sau khi backend xác nhận, đưa xe
 *   vào từ trái, phanh, xoay đuôi về phía người xem và chạy vào chiều sâu.
 *
 * TODO [BACKEND/MEDIA]: có thể thay `config.src` bằng model3dUrl cùng origin/CDN.
 * CORS phải cho phép GET + Range; giữ animationPreset trong whitelist frontend.
 */
import { useEffect, useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { ArrowCounterClockwise, CursorClick, SpinnerGap } from '@phosphor-icons/react'
import { SmartImage } from './SmartImage'
import { chargingStation3dModel, getVehicle3dModel } from '../data/vehicle3d'
import { getClientDeviceProfile } from '../utils/deviceProfile'

gsap.registerPlugin(useGSAP, ScrollTrigger)

let modelViewerModule
const loadModelViewer = () => {
  modelViewerModule ||= import('@google/model-viewer')
  return modelViewerModule
}

export const preloadVehicle3dRuntime = () => loadModelViewer()

const applyModelFinish = (viewer, config) => {
  const finish = config?.paint
  if (!finish || !viewer?.model) return

  const material = viewer.model.getMaterialByName?.(finish.materialName)
  const pbr = material?.pbrMetallicRoughness
  if (!pbr) return

  if (finish.removeBaseColorTexture) pbr.baseColorTexture?.setTexture(null)
  pbr.setBaseColorFactor(finish.baseColor)
  pbr.setMetallicFactor(finish.metallicFactor)
  pbr.setRoughnessFactor(finish.roughnessFactor)
}

const splitOrbit = (orbit) => {
  const [azimuth, ...rest] = orbit.trim().split(/\s+/)
  return {
    azimuth: Number.parseFloat(azimuth),
    suffix: rest.join(' '),
  }
}

const nearestEquivalentAngle = (from, to) => {
  const delta = ((((to - from) + 180) % 360) + 360) % 360 - 180
  return from + delta
}

function ModelSurface({
  car,
  config,
  viewerRef,
  interactive = true,
  eager = false,
  initialOrbit,
  onReady,
  onFailure,
  posterMode = 'media',
  quiet = false,
  interactionPrompt = 'auto',
  autoRotate = true,
  staticMode = false,
}) {
  const internalRef = useRef(null)
  const [engineReady, setEngineReady] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (staticMode) return undefined
    let active = true
    loadModelViewer()
      .then(() => { if (active) setEngineReady(true) })
      .catch(() => {
        if (!active) return
        setFailed(true)
        onFailure?.()
      })
    return () => { active = false }
  }, [onFailure, staticMode])

  useEffect(() => {
    if (staticMode) return undefined
    const viewer = internalRef.current
    if (!viewer || !engineReady) return undefined

    const handleLoad = () => {
      applyModelFinish(viewer, config)
      setLoaded(true)
      setFailed(false)
      onReady?.(viewer)
    }
    const handleError = () => {
      setFailed(true)
      onFailure?.()
    }
    viewer.addEventListener('load', handleLoad)
    viewer.addEventListener('error', handleError)
    if (viewer.loaded) handleLoad()
    return () => {
      viewer.removeEventListener('load', handleLoad)
      viewer.removeEventListener('error', handleError)
    }
  }, [engineReady, onFailure, onReady, staticMode])

  const setRef = (node) => {
    internalRef.current = node
    if (viewerRef) viewerRef.current = node
  }

  if (staticMode) {
    return (
      <div className="vehicle-model-surface vehicle-model-surface--static">
        <SmartImage
          className="vehicle-model-surface__static-image"
          src={car.motionImage || car.intro}
          alt={`${car.name} — ảnh tối ưu cho thiết bị`}
          eager={eager}
          fit="contain"
        />
      </div>
    )
  }

  return (
    <div className={`vehicle-model-surface ${loaded ? 'is-loaded' : ''} ${failed ? 'has-error' : ''}`}>
      <model-viewer
        ref={setRef}
        src={engineReady && !failed ? config.src : undefined}
        poster={posterMode === 'media' ? car.motionImage || car.intro : undefined}
        alt={`Mô hình 3D tương tác của ${car.name}`}
        loading={eager ? 'eager' : 'lazy'}
        reveal="auto"
        camera-controls={interactive ? '' : undefined}
        disable-pan=""
        touch-action="pan-y"
        auto-rotate={interactive && autoRotate ? '' : undefined}
        auto-rotate-delay="1600"
        rotation-per-second="14deg"
        interaction-prompt={interactive ? interactionPrompt : 'none'}
        interaction-prompt-style="basic"
        camera-orbit={initialOrbit || config.orbit}
        camera-target={config.cameraTarget}
        field-of-view={config.fieldOfView}
        min-field-of-view="20deg"
        max-field-of-view="42deg"
        shadow-intensity={config.shadowIntensity || '1.15'}
        shadow-softness="0.88"
        exposure={config.exposure || '1.04'}
        environment-image={config.environmentImage}
        tone-mapping="aces"
      >
        <div className={`vehicle-model-surface__poster is-${posterMode}`} slot="poster">
          {posterMode === 'media' && (
            <SmartImage src={car.motionImage || car.intro} alt="" aria-hidden="true" fit="contain" />
          )}
        </div>
        <div className="vehicle-model-surface__progress" slot="progress-bar" aria-hidden="true">
          <span />
        </div>
      </model-viewer>
      {!quiet && !loaded && !failed && (
        <span className="vehicle-model-surface__status"><SpinnerGap size={16} /> Đang dựng không gian 3D</span>
      )}
      {!quiet && failed && <span className="vehicle-model-surface__status">Không thể tải model 3D</span>}
    </div>
  )
}

export function Vehicle3DExperience({ car, onEnter }) {
  const config = getVehicle3dModel(car?.id)
  const root = useRef(null)
  const viewer = useRef(null)
  const [interactive, setInteractive] = useState(false)
  const deviceProfile = getClientDeviceProfile()
  const reducedMotion = deviceProfile.reducedMotion
  const staticFallback = deviceProfile.constrained

  useEffect(() => {
    if (!config || staticFallback) return undefined
    const fallback = window.setTimeout(() => setInteractive(true), 4500)
    return () => window.clearTimeout(fallback)
  }, [car?.id, config, staticFallback])

  useGSAP(
    () => {
      if (!config) return undefined
      const { compact, constrained, reducedMotion: reduced } = getClientDeviceProfile()
      const stage = root.current?.querySelector('.vehicle-3d__viewer')
      const copy = root.current?.querySelector('.vehicle-3d__copy')
      const streaks = root.current?.querySelectorAll('.vehicle-3d__streak')
      if (!stage) return undefined

      if (reduced || constrained) {
        gsap.set([stage, copy], { opacity: 1, xPercent: 0, y: 0, scale: 1 })
        gsap.set(streaks, { opacity: 0 })
        setInteractive(!constrained)
        return undefined
      }

      if (compact) {
        gsap.set(streaks, { opacity: 0 })
        const timeline = gsap.timeline({ paused: true, onComplete: () => setInteractive(true) })
          .fromTo(stage, { y: 26, scale: 0.96, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: 0.55, ease: 'power3.out' })
          .fromTo(copy, { y: 16, opacity: 0 }, { y: 0, opacity: 1, duration: 0.42, ease: 'power3.out' }, 0.08)
        const trigger = ScrollTrigger.create({
          trigger: root.current,
          start: 'top 82%',
          once: true,
          onEnter: () => {
            onEnter?.()
            timeline.play(0)
          },
        })
        return () => {
          trigger.kill()
          timeline.kill()
        }
      }

      gsap.set(copy, { opacity: 0, y: 34 })
      gsap.set(streaks, { scaleX: 0, opacity: 0, transformOrigin: 'left center' })

      const timeline = gsap.timeline({
        paused: true,
        defaults: { ease: 'power3.inOut' },
        onStart: () => {
          if (viewer.current) {
            viewer.current.cameraOrbit = config.sideOrbit
            viewer.current.jumpCameraToGoal?.()
          }
        },
        onComplete: () => setInteractive(true),
      })

      timeline
        .fromTo(
          stage,
          { xPercent: -148, scale: 0.56, opacity: 0.92 },
          { xPercent: 152, scale: 0.56, opacity: 1, duration: 2.55, ease: 'power2.inOut' },
        )
        .fromTo(
          streaks,
          { scaleX: 0, opacity: 0 },
          { scaleX: 1, opacity: 0.48, duration: 0.76, stagger: 0.08, ease: 'power2.out' },
          0.34,
        )
        .to(streaks, { opacity: 0, duration: 0.62 }, 1.72)
        .set(stage, { xPercent: 0, scale: 0.72, opacity: 0 })
        .call(() => {
          if (viewer.current) viewer.current.cameraOrbit = config.orbit
        })
        .to(stage, { scale: 1, opacity: 1, duration: 1.25, ease: 'expo.out' })
        .to(copy, { y: 0, opacity: 1, duration: 0.78, ease: 'power4.out' }, '-=0.58')

      const trigger = ScrollTrigger.create({
        trigger: root.current,
        // Bắt đầu khi sân khấu đã nằm rõ trong viewport để người dùng nhìn đủ
        // toàn bộ nhịp xe chạy ngang 2,55 giây, thay vì chỉ thấy đoạn cuối.
        start: 'top 52%',
        once: true,
        onEnter: () => {
          onEnter?.()
          timeline.play(0)
        },
      })

      return () => {
        trigger.kill()
        timeline.kill()
      }
    },
    { scope: root, dependencies: [car?.id, staticFallback] },
  )

  if (!config) return null

  const resetCamera = () => {
    if (!viewer.current) return
    viewer.current.cameraOrbit = config.orbit
    viewer.current.fieldOfView = config.fieldOfView
    viewer.current.jumpCameraToGoal?.()
  }

  return (
    <section className={`vehicle-3d ${interactive ? 'is-interactive' : ''} ${staticFallback ? 'is-static' : ''}`} ref={root} aria-labelledby={`vehicle-3d-${car.id}`}>
      <div className="vehicle-3d__ambient" aria-hidden="true" />
      <div className="vehicle-3d__streaks" aria-hidden="true">
        <span className="vehicle-3d__streak" /><span className="vehicle-3d__streak" /><span className="vehicle-3d__streak" />
      </div>
      <div className="section-frame vehicle-3d__inner">
        <div className="vehicle-3d__copy">
          <p className="eyebrow">{staticFallback ? 'Góc nhìn tối ưu' : 'Góc nhìn tương tác'}</p>
          <h2 id={`vehicle-3d-${car.id}`}>{car.name}, hiện diện trong không gian ba chiều.</h2>
          <p>{staticFallback ? 'Ảnh studio nhẹ hơn được dùng để giữ trải nghiệm mượt trên thiết bị này.' : 'Giữ và kéo để xoay · cuộn để tiến gần hoặc lùi xa.'}</p>
        </div>
        <div className="vehicle-3d__viewer">
          <ModelSurface
            car={car}
            config={config}
            viewerRef={viewer}
            interactive={interactive && !staticFallback}
            autoRotate={!reducedMotion && !staticFallback}
            eager
            initialOrbit={config.sideOrbit}
            posterMode="dark"
            staticMode={staticFallback}
          />
          {!staticFallback && (
            <>
              <div className="vehicle-3d__controls">
                <span><CursorClick size={17} weight="light" /> Kéo để quan sát</span>
                <button type="button" onClick={resetCamera}><ArrowCounterClockwise size={16} weight="light" /> Đặt lại góc nhìn</button>
              </div>
              <a className="vehicle-3d__credit" href={config.credit.source} target="_blank" rel="noreferrer">
                3D: {config.credit.author} · {config.credit.license}
              </a>
            </>
          )}
        </div>
      </div>
    </section>
  )
}

export function ChargingStation3DExperience({ poster }) {
  const root = useRef(null)
  const viewer = useRef(null)
  const [interactive, setInteractive] = useState(false)
  const deviceProfile = getClientDeviceProfile()
  const staticFallback = deviceProfile.constrained
  const station = {
    id: 'charging-station',
    name: 'Trạm sạc VinFast',
    motionImage: poster,
    intro: poster,
  }

  useGSAP(
    () => {
      const stage = root.current?.querySelector('.charging-station-3d__stage')
      const copy = root.current?.querySelector('.charging-station-3d__copy')
      if (!stage) return undefined

      const { compact, constrained, reducedMotion } = getClientDeviceProfile()
      if (reducedMotion || constrained) {
        gsap.set([stage, copy], { opacity: 1, y: 0, scale: 1 })
        setInteractive(!constrained)
        return undefined
      }

      if (compact) {
        const timeline = gsap.timeline({ paused: true, onComplete: () => setInteractive(true) })
          .fromTo(copy, { y: 16, opacity: 0 }, { y: 0, opacity: 1, duration: 0.42, ease: 'power3.out' })
          .fromTo(stage, { y: 24, scale: 0.97, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: 0.52, ease: 'power3.out' }, 0.08)
        const trigger = ScrollTrigger.create({
          trigger: root.current,
          start: 'top 84%',
          once: true,
          onEnter: () => timeline.play(0),
        })
        return () => {
          trigger.kill()
          timeline.kill()
        }
      }

      const timeline = gsap.timeline({ paused: true, onComplete: () => setInteractive(true) })
      timeline
        .fromTo(copy, { y: 38, opacity: 0 }, { y: 0, opacity: 1, duration: 0.9, ease: 'power3.out' })
        .fromTo(
          stage,
          { y: 76, scale: 0.86, opacity: 0 },
          { y: 0, scale: 1, opacity: 1, duration: 1.55, ease: 'power4.out' },
          0.18,
        )

      const trigger = ScrollTrigger.create({
        trigger: root.current,
        start: 'top 72%',
        once: true,
        onEnter: () => timeline.play(0),
      })

      return () => {
        trigger.kill()
        timeline.kill()
      }
    },
    { scope: root, dependencies: [staticFallback] },
  )

  const resetCamera = (target, orbit, fieldOfView) => {
    if (!target.current) return
    target.current.cameraOrbit = orbit
    target.current.fieldOfView = fieldOfView
    target.current.jumpCameraToGoal?.()
  }

  return (
    <section id="charging-3d" className={`vehicle-3d vehicle-3d--station ${interactive ? 'is-interactive' : ''} ${staticFallback ? 'is-static' : ''}`} ref={root} aria-labelledby="charging-station-3d-title">
      <div className="vehicle-3d__ambient" aria-hidden="true" />
      <div className="section-frame charging-station-3d__inner">
        <header className="charging-station-3d__copy">
          <p className="eyebrow">Trạm sạc tương tác</p>
          <h2 id="charging-station-3d-title">Quan sát toàn bộ trạm sạc.</h2>
          <p>{staticFallback ? 'Ảnh toàn cảnh nhẹ hơn được dùng để giữ trang ổn định trên thiết bị này.' : 'Một góc nhìn cân đối cho toàn bộ hệ thống. Giữ và kéo trực tiếp trên mô hình để xem thiết bị từ mọi phía.'}</p>
        </header>

        <div className="charging-station-3d__grid">
          <article className="charging-station-3d__stage charging-station-3d__stage--overview">
            <div className="charging-station-3d__label">
              <span>{staticFallback ? 'Ảnh toàn cảnh' : 'Mô hình tương tác'}</span>
              <strong>Hạ tầng trạm sạc</strong>
            </div>
            <ModelSurface
              car={station}
              config={chargingStation3dModel}
              viewerRef={viewer}
              interactive={interactive && !staticFallback}
              eager
              initialOrbit={chargingStation3dModel.orbit}
              posterMode="dark"
              interactionPrompt="none"
              staticMode={staticFallback}
            />
            {!staticFallback && (
              <div className="charging-station-3d__controls">
                <span><CursorClick size={17} weight="light" /> Giữ và kéo để xoay</span>
                <button
                  type="button"
                  onClick={() => resetCamera(viewer, chargingStation3dModel.orbit, chargingStation3dModel.fieldOfView)}
                >
                  <ArrowCounterClockwise size={16} weight="light" /> Về toàn cảnh
                </button>
              </div>
            )}
          </article>
        </div>

        {!staticFallback && <span className="charging-station-3d__credit">3D · {chargingStation3dModel.credit.author}</span>}
      </div>
    </section>
  )
}

/**
 * Model 3D cỡ nhỏ dùng riêng ở phiếu booking thành công. Chỉ những mẫu có GLB
 * được duyệt; các mẫu khác tiếp tục dùng ảnh studio alpha ở BookingPage.
 * Kích thước do ô .studio-vehicle__stage sở hữu để không làm lệch bố cục phiếu.
 */
export function BookingSuccessVehicleModel({ car, className = '' }) {
  const config = getVehicle3dModel(car?.id)
  const [failed, setFailed] = useState(false)
  const useLiteModel = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches
    || navigator.connection?.saveData === true

  useEffect(() => setFailed(false), [car?.id])

  if (!config || failed || useLiteModel) {
    return (
      <SmartImage
        className={`booking-success-model__fallback vehicle-shot vehicle-shot--${car?.studioShot?.mode || 'cutout'} ${className}`.trim()}
        src={car?.studioShot?.src || car?.intro}
        alt={`${car?.name || 'VinFast'} — ảnh studio`}
        eager
        fit="contain"
      />
    )
  }

  return (
    <div className={`booking-success-model ${className}`.trim()} aria-label={`Mô hình 3D ${car.name}`}>
      <ModelSurface
        car={car}
        config={config}
        interactive
        eager
        initialOrbit={config.orbit}
        onFailure={() => setFailed(true)}
        interactionPrompt="none"
        quiet
      />
      <span className="booking-success-model__hint">Giữ và kéo để xoay xe</span>
    </div>
  )
}

export function BookingSuccessCinematic({ car, onComplete }) {
  const config = getVehicle3dModel(car?.id)
  const root = useRef(null)
  const viewer = useRef(null)
  const [modelReady, setModelReady] = useState(!config)
  const [modelFailed, setModelFailed] = useState(false)

  useEffect(() => {
    setModelReady(!config)
    setModelFailed(false)
  }, [car?.id, config])

  useGSAP(
    () => {
      const reveal = gsap.fromTo(root.current, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.36, ease: 'power2.out' })
      return () => reveal.kill()
    },
    { scope: root, dependencies: [car?.id] },
  )

  useGSAP(
    () => {
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (reduced) {
        const timer = window.setTimeout(onComplete, 180)
        return () => window.clearTimeout(timer)
      }

      if (config && !modelFailed && !modelReady) return undefined

      const vehicle = root.current?.querySelector('.booking-cinematic__vehicle')
      const copy = root.current?.querySelector('.booking-cinematic__copy')
      const brake = root.current?.querySelectorAll('.booking-cinematic__brake span')
      const speedLines = root.current?.querySelectorAll('.booking-cinematic__speed span')
      const sparks = root.current?.querySelectorAll('.booking-cinematic__sparks span')
      const lightSweep = root.current?.querySelector('.booking-cinematic__light-sweep')
      const roadGlow = root.current?.querySelector('.booking-cinematic__road-glow')
      const depthLines = root.current?.querySelectorAll('.booking-cinematic__depth span')
      if (!vehicle) return undefined

      if (viewer.current && config) {
        viewer.current.cameraOrbit = config.sideOrbit
        viewer.current.jumpCameraToGoal?.()
      }

      const sideOrbit = config ? splitOrbit(config.sideOrbit) : null
      const rearOrbit = config ? splitOrbit(config.rearOrbit) : null
      const camera = sideOrbit ? { azimuth: sideOrbit.azimuth } : null
      const rearAzimuth = sideOrbit && rearOrbit
        ? nearestEquivalentAngle(sideOrbit.azimuth, rearOrbit.azimuth)
        : 0

      const timeline = gsap.timeline({ defaults: { ease: 'power3.inOut' } })
      gsap.set(speedLines, { xPercent: -150, scaleX: 0.16, opacity: 0, transformOrigin: 'left center' })
      gsap.set(sparks, { x: 0, y: 0, scaleX: 0.2, opacity: 0, transformOrigin: 'right center' })
      gsap.set(lightSweep, { xPercent: -180, opacity: 0 })
      gsap.set(roadGlow, { scaleX: 0.18, opacity: 0, transformOrigin: 'center' })
      gsap.set(depthLines, { scaleX: 0.18, opacity: 0, transformOrigin: 'center' })
      timeline
        .call(() => {
          if (root.current) root.current.dataset.phase = 'side-drive'
        })
        .fromTo(copy, { y: 22, opacity: 0 }, { y: 0, opacity: 1, duration: 0.55 }, 0)
        .fromTo(
          vehicle,
          { xPercent: -124, scale: 0.58, opacity: 0.95, transformOrigin: '50% 52%' },
          { xPercent: -22, scale: 0.7, opacity: 1, duration: 1.55, ease: 'power2.in' },
          0.18,
        )
        // Hai nhịp tăng tốc → rà phanh tạo cảm giác khối lượng thật, thay vì xe
        // trượt đều như một layer phẳng.
        .to(vehicle, { xPercent: 0, scale: 0.74, duration: 0.9, ease: 'power4.out' })
        .fromTo(
          speedLines,
          { xPercent: -150, scaleX: 0.16, opacity: 0 },
          { xPercent: 190, scaleX: 1, opacity: 0.58, duration: 0.62, repeat: 3, repeatDelay: 0.04, stagger: 0.045, ease: 'power2.in' },
          0.2,
        )
        .fromTo(roadGlow, { scaleX: 0.18, opacity: 0 }, { scaleX: 1, opacity: 0.42, duration: 1.85, ease: 'power2.out' }, 0.3)
        .fromTo(lightSweep, { xPercent: -180, opacity: 0 }, { xPercent: 190, opacity: 0.72, duration: 1.7, ease: 'power2.inOut' }, 0.48)
        .to(speedLines, { opacity: 0, duration: 0.28 }, 2.25)
        .to(lightSweep, { opacity: 0, duration: 0.24 }, 2.1)
        // Phanh ở đúng tâm: hơi dồn trọng lượng rồi trả thân xe về xPercent 0.
        .to(vehicle, { xPercent: 1.15, rotateZ: -0.42, duration: 0.14, ease: 'power2.out' })
        .to(vehicle, { xPercent: 0, rotateZ: 0, duration: 0.5, ease: 'elastic.out(1, 0.48)' })
        .fromTo(brake, { scaleX: 0, opacity: 0 }, { scaleX: 1, opacity: 0.78, duration: 0.36, stagger: 0.05 }, '-=0.46')
        .fromTo(
          sparks,
          { x: 0, y: 0, scaleX: 0.2, opacity: 0 },
          {
            x: (index) => (index - 3.5) * 25,
            y: (index) => -8 - ((index % 3) * 9),
            rotation: (index) => -18 + (index * 6),
            scaleX: 1.7,
            opacity: 0.78,
            duration: 0.52,
            stagger: 0.018,
            ease: 'power3.out',
          },
          '-=0.4',
        )
        .to(sparks, { opacity: 0, scaleX: 0.4, duration: 0.22 }, '-=0.2')
        .to(roadGlow, { scaleX: 0.62, opacity: 0.2, duration: 0.5 }, '-=0.44')
        .to({}, { duration: 0.34 })
        // Xe đứng nguyên giữa màn hình trong lúc camera đi từ mặt cửa sang đuôi.
        .call(() => {
          if (root.current) root.current.dataset.phase = 'rear-turn'
        })
        .to(camera || {}, {
          azimuth: rearAzimuth,
          duration: config ? 1.2 : 0,
          ease: 'power2.inOut',
          onUpdate: () => {
            if (!viewer.current || !camera || !rearOrbit) return
            viewer.current.cameraOrbit = `${camera.azimuth}deg ${rearOrbit.suffix}`
            // GSAP đã nội suy góc theo từng frame, nên nhảy camera tới goal ngay
            // để đuôi xe chạm đúng hướng trước khi bắt đầu thu nhỏ vào chiều sâu.
            viewer.current.jumpCameraToGoal?.()
          },
        })
        .to(vehicle, { scale: 0.76, duration: 0.24, ease: 'power2.out' }, '<')
        .to(brake, { opacity: 0, duration: 0.34 }, '-=0.22')
        .to({}, { duration: 0.24 })
        // Đuôi xe hướng về người xem, sau đó xe chạy thẳng vào chiều sâu.
        .call(() => {
          if (root.current) root.current.dataset.phase = 'rear-retreat'
        })
        .fromTo(depthLines, { scaleX: 0.18, opacity: 0 }, { scaleX: 1, opacity: 0.38, duration: 0.72, stagger: 0.08, ease: 'power2.out' })
        .to(vehicle, {
          xPercent: 0,
          scale: 0.045,
          yPercent: -10,
          opacity: 0,
          filter: 'blur(9px)',
          duration: 1.82,
          ease: 'power2.in',
        }, '<+=0.06')
        .to(depthLines, { scaleX: 0.06, opacity: 0, duration: 1.34, stagger: 0.04, ease: 'power2.in' }, '<+=0.18')
        .to(roadGlow, { scaleX: 0.08, opacity: 0, duration: 1.42, ease: 'power2.in' }, '<')
        .to(copy, { opacity: 0, y: -12, duration: 0.35 }, '-=0.62')
        .to(root.current, { autoAlpha: 0, duration: 0.46, ease: 'power2.inOut' })
        .call(onComplete)

      return () => timeline.kill()
    },
    { scope: root, dependencies: [car?.id, config, modelFailed, modelReady, onComplete] },
  )

  if (!car) return null

  return (
    <div className="booking-cinematic" ref={root} role="status" aria-live="polite" aria-label="Đang hoàn tất lịch lái thử">
      <div className="booking-cinematic__horizon" aria-hidden="true" />
      <div className="booking-cinematic__speed" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
      <div className="booking-cinematic__road-glow" aria-hidden="true" />
      <div className="booking-cinematic__light-sweep" aria-hidden="true" />
      <div className="booking-cinematic__copy">
        <span>Lịch đã được xác nhận</span>
        <strong>{car.name} đang khép lại hành trình đặt lịch.</strong>
      </div>
      <div className={`booking-cinematic__vehicle ${config && !modelFailed ? 'has-model' : 'has-image'}`}>
        {config && !modelFailed ? (
          <ModelSurface
            car={car}
            config={config}
            viewerRef={viewer}
            interactive={false}
            eager
            initialOrbit={config.sideOrbit}
            onReady={() => setModelReady(true)}
            onFailure={() => {
              setModelFailed(true)
              setModelReady(true)
            }}
            posterMode="dark"
            quiet
          />
        ) : (
          <SmartImage src={car.motionImage || car.intro} alt="" aria-hidden="true" fit="contain" />
        )}
      </div>
      <div className="booking-cinematic__brake" aria-hidden="true"><span /><span /></div>
      <div className="booking-cinematic__sparks" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /><span /></div>
      <div className="booking-cinematic__depth" aria-hidden="true"><span /><span /><span /></div>
    </div>
  )
}
