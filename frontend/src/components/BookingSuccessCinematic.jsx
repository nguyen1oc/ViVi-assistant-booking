/**
 * Đoạn phim ngắn chạy ngay sau khi đặt lịch thành công.
 *
 * RANH GIỚI: chỉ nhận mẫu xe đã xác nhận và một callback `onComplete`. Không tạo, không sửa,
 * không thử lại booking. BookingPage vẫn sở hữu toàn bộ state; component này chỉ làm chậm màn
 * phiếu lịch lại cho tới khi hình chạy xong.
 *
 * ══ MỘT ĐOẠN PHIM DUY NHẤT CHO MỌI MẪU XE (đổi 18/08/2026) ══
 * Trước đây phim dựng theo model 3D của CHÍNH mẫu vừa đặt, mà chỉ VF 3 và VF 9 có file .glb —
 * 12 mẫu còn lại rơi về một tấm ảnh tĩnh trượt ngang, nên cùng một bước đặt lịch lại ra hai
 * chất lượng rất khác nhau. Anh Minh chốt: thống nhất tất cả về logo VinFast + xe Lạc Hồng.
 *
 * ══ VÌ SAO LÀ ẢNH 360 CHỨ KHÔNG PHẢI .glb ══
 * Kho chỉ có ba file .glb: vf3, vf9 và trạm sạc — KHÔNG có model Lạc Hồng (đã tìm cả trong
 * `frontend/Ảnh xe vinfast/`). Bù lại Lạc Hồng có sẵn bộ 5 khung render 360 độ nền trong suốt,
 * chính là thứ dựng nên khối xoay xe ở trang chủ. Phim này dùng lại đúng bộ đó.
 *
 * ══ CHIỀU CHẠY: TRÁI → PHẢI ══ (anh Minh chốt 18/08/2026, giống VF 3 và VF 9)
 * Bộ 360 không có khung hông nào mũi hướng phải, nên khung hông được LẬT NGANG. Lật được vì
 * đã soi ba vùng của khung hông ở cỡ x2 (đầu xe · thân xe · đuôi xe) và KHÔNG có chữ nào đọc
 * ra — chỉ có nẹp vàng, mâm xe và logo chữ V đối xứng. Khung đuôi thì KHÔNG lật, vì biển số
 * "Lạc Hồng 900 LX" phải đọc xuôi.
 *
 * ══ CHỌN KHUNG NÀO, VÌ SAO ══ (soi từng khung ở cỡ lớn trước khi quyết, không đoán theo tên)
 *   spin-2 (lật) → hông xe ĐẦY ĐỦ, thấy trọn dãy cửa, mũi hướng PHẢI — khớp chiều xe chạy.
 *   spin-3       → đuôi xe quay về phía người xem, thân lùi chéo sang PHẢI. Đây đúng là cú
 *                  xoay của một chiếc xe mũi hướng phải.
 *   spin-4       → cũng là 3/4 sau nhưng thân lùi sang TRÁI, tức thuộc chiều xoay NGƯỢC LẠI.
 *                  Dùng nó ở đây xe sẽ như bị lộn đầu đuôi giữa chừng.
 * Mạch đúng: hông lướt ngang → tới giữa thì đuôi xoay vào mắt người xem → lùi vào chiều sâu.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { showcaseImage, vehicleImage } from '../media/assets'
import { useDialogFocus } from '../hooks/useDialogFocus'
import './BookingSuccessCinematic.css'

const vinfastWordmark = vehicleImage('Vinfast-logo-new_NO_Tagline -2D-Horizontal black.png')

/*
 * Hai khung dựng nên cú xoay, đã CHUẨN HOÁ sẵn thành file riêng thay vì dùng thẳng spin-2/spin-4.
 * Lý do: hai khung gốc khác tỉ lệ (1692×929 và 1542×1020) nên khi cùng `object-fit: contain`
 * trong một khung, chiếc xe hiện ra lệch nhau 16% chiều cao và lệch 25px đường chạm đất — lúc
 * chồng mờ trông như hai tấm ảnh khác cỡ nhảy vào nhau chứ không phải một chiếc xe đang xoay.
 * Hai file dưới đây đặt xe CÙNG chiều cao trên CÙNG một đường nền, trong cùng một khung 1760×900.
 * Dựng lại bằng đoạn script ghi trong ghi chú đầu file (crop theo alpha → scale về cao 545 →
 * dán đáy xe ở y=760).
 */
const lacHongSideFrame = showcaseImage('lac-hong-900lx/film-side.png')
const lacHongRearFrame = showcaseImage('lac-hong-900lx/film-rear.png')

const createSeededRandom = (text) => {
  let state = [...text].reduce((value, char) => ((value * 31) + char.charCodeAt(0)) >>> 0, 2166136261)
  return () => {
    state = ((state * 1664525) + 1013904223) >>> 0
    return state / 4294967296
  }
}

/** A small deterministic particle renderer keeps smoke physical and repeatable. */
const useTyreSmoke = (canvasRef, rootRef, vehicleRef, controlRef, vehicleId) => {
  useEffect(() => {
    if (
      window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 900px), (pointer: coarse)').matches
      || navigator.connection?.saveData === true
    ) return undefined

    const canvas = canvasRef.current
    const root = rootRef.current
    if (!canvas || !root) return undefined

    const context = canvas.getContext('2d', { alpha: true })
    if (!context) return undefined

    const random = createSeededRandom(vehicleId || 'vinfast')
    const particles = []
    const tyreTrails = [[], []]
    const sprite = document.createElement('canvas')
    const spriteSize = 128
    sprite.width = spriteSize
    sprite.height = spriteSize
    const spriteContext = sprite.getContext('2d')
    const spriteGradient = spriteContext.createRadialGradient(64, 64, 3, 64, 64, 61)
    spriteGradient.addColorStop(0, 'rgba(214, 218, 220, 0.32)')
    spriteGradient.addColorStop(0.42, 'rgba(151, 157, 161, 0.17)')
    spriteGradient.addColorStop(1, 'rgba(74, 78, 82, 0)')
    spriteContext.fillStyle = spriteGradient
    spriteContext.fillRect(0, 0, spriteSize, spriteSize)

    let width = 0
    let height = 0
    let dpr = 1
    let frame = 0
    let previousTime = performance.now()
    let spawnCarry = 0
    let trailCarry = 0

    const resize = () => {
      const rect = root.getBoundingClientRect()
      width = rect.width
      height = rect.height
      dpr = Math.min(window.devicePixelRatio || 1, 1.5)
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      context.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const getContactPoints = () => {
      const control = controlRef.current
      const rearView = control.rearMix
      const rect = vehicleRef.current?.getBoundingClientRect()
      if (!rect) return [{ x: width * 0.5, y: height * 0.68 }, { x: width * 0.5, y: height * 0.68 }]

      // Khung hông đã lật nên mũi xe hướng PHẢI: trục sau nằm bên trái tâm khung. Khi khung
      // chuyển dần sang góc đuôi, một vệt tiếp đất tách thành hai bánh sau. Mọi toạ độ lấy từ
      // rect thật của chiếc xe nên khói không bao giờ trôi rời khỏi bánh.
      const sideX = rect.left + (rect.width * 0.355)
      const rearCenterX = rect.left + (rect.width * 0.5)
      const centerX = sideX + ((rearCenterX - sideX) * rearView)
      const separation = rect.width * 0.082 * rearView
      const y = rect.top + (rect.height * (0.705 + (rearView * 0.018)))
      return [{ x: centerX - separation, y }, { x: centerX + separation, y }]
    }

    const spawnParticle = () => {
      const control = controlRef.current
      const rearView = control.rearMix
      const contacts = getContactPoints()
      const contact = contacts[random() > 0.5 ? 1 : 0]
      const size = 26 + (random() * 54)
      particles.push({
        x: contact.x + ((random() - 0.5) * Math.min(width * 0.026, 30)),
        y: contact.y + ((random() - 0.5) * Math.min(height * 0.018, 15)),
        // Xe chạy sang PHẢI nên khói tản ngược về bên trái.
        vx: (-34 - (random() * 58)) * (1 - (rearView * 0.72)),
        vy: -12 - (random() * 30),
        size,
        growth: 22 + (random() * 30),
        life: 0,
        ttl: 0.78 + (random() * 0.62),
        opacity: 0.34 + (random() * 0.3),
        rotation: random() * Math.PI * 2,
        spin: (random() - 0.5) * 0.8,
      })
    }

    const render = (time) => {
      const delta = Math.min((time - previousTime) / 1000, 0.035)
      previousTime = time
      context.clearRect(0, 0, width, height)

      const intensity = controlRef.current.intensity
      spawnCarry += intensity * delta * 88
      while (spawnCarry >= 1 && particles.length < 110) {
        spawnParticle()
        spawnCarry -= 1
      }

      const skid = controlRef.current.skid
      trailCarry += skid * delta * 56
      while (trailCarry >= 1) {
        const contacts = getContactPoints()
        contacts.forEach((point, index) => tyreTrails[index].push({ ...point, life: 0 }))
        trailCarry -= 1
      }

      tyreTrails.forEach((trail) => {
        for (let index = trail.length - 1; index >= 0; index -= 1) {
          trail[index].life += delta
          if (trail[index].life > 1.65) trail.splice(index, 1)
        }
        if (trail.length < 2) return
        context.beginPath()
        trail.forEach((point, index) => {
          if (index === 0) context.moveTo(point.x, point.y)
          else context.lineTo(point.x, point.y)
        })
        context.lineWidth = 1
        context.strokeStyle = `rgba(255, 255, 255, ${0.075 * Math.min(skid + 0.2, 1)})`
        context.stroke()
      })

      for (let index = particles.length - 1; index >= 0; index -= 1) {
        const particle = particles[index]
        particle.life += delta
        if (particle.life >= particle.ttl) {
          particles.splice(index, 1)
          continue
        }
        const progress = particle.life / particle.ttl
        particle.x += particle.vx * delta
        particle.y += particle.vy * delta
        particle.size += particle.growth * delta
        particle.rotation += particle.spin * delta
        const alpha = Math.sin(progress * Math.PI) * particle.opacity
        context.save()
        context.globalAlpha = alpha
        context.translate(particle.x, particle.y)
        context.rotate(particle.rotation)
        context.drawImage(sprite, -particle.size / 2, -particle.size / 2, particle.size, particle.size)
        context.restore()
      }

      frame = window.requestAnimationFrame(render)
    }

    resize()
    window.addEventListener('resize', resize)
    frame = window.requestAnimationFrame(render)
    return () => {
      window.cancelAnimationFrame(frame)
      window.removeEventListener('resize', resize)
    }
  }, [canvasRef, controlRef, rootRef, vehicleId, vehicleRef])
}

export function BookingSuccessCinematic({ car, onComplete }) {
  const root = useRef(null)
  const dialogRef = useDialogFocus({ onClose: onComplete })
  const setRootNode = useCallback((node) => {
    root.current = node
    dialogRef.current = node
  }, [dialogRef])
  const vehicle = useRef(null)
  const canvas = useRef(null)
  const smoke = useRef({ intensity: 0, rearMix: 0, skid: 0 })
  const mobileLite = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches
    || navigator.connection?.saveData === true
  // Chỉ chạy phim khi CẢ HAI khung đã nằm trong bộ nhớ đệm, nếu không cú xoay giữa phim sẽ
  // hiện ra một khoảng trống đúng lúc người xem đang nhìn chăm chú nhất.
  const [framesReady, setFramesReady] = useState(false)

  useTyreSmoke(canvas, root, vehicle, smoke, 'lac-hong-900lx')

  useEffect(() => {
    let active = true
    // Mobile chỉ dùng khung hông để giữ animation nhẹ, nhưng vẫn phải chờ ảnh thật tải xong.
    // Bản cũ đánh dấu ready ngay lập tức rồi không render rig, nên mobile chỉ thấy mỗi logo.
    let pending = mobileLite ? 1 : 2
    const done = () => { pending -= 1; if (pending <= 0 && active) setFramesReady(true) }
    const preload = (src) => {
      const image = new Image()
      image.onload = done
      image.onerror = done
      image.src = src
    }
    preload(lacHongSideFrame)
    if (!mobileLite) preload(lacHongRearFrame)
    // Mạng chậm cũng không được treo màn chờ: quá 4 giây thì cứ chạy.
    const timeout = window.setTimeout(() => { if (active) setFramesReady(true) }, 4000)
    return () => { active = false; window.clearTimeout(timeout) }
  }, [mobileLite])

  useGSAP(
    () => {
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (reduced) {
        gsap.set(root.current, { autoAlpha: 1 })
        const timer = window.setTimeout(onComplete, 260)
        return () => window.clearTimeout(timer)
      }

      if (!framesReady) return undefined

      const movingVehicle = vehicle.current
      const brandPrelude = root.current?.querySelector('.booking-film__brand')
      const air = root.current?.querySelector('.booking-film__air')
      const airLines = root.current?.querySelectorAll('.booking-film__air span')
      const sideFrame = root.current?.querySelector('[data-frame="side"]')
      const rearFrame = root.current?.querySelector('[data-frame="rear"]')
      const confirmation = root.current?.querySelector('.booking-film__confirmation')
      const confirmationRule = confirmation?.querySelector('i')

      if (mobileLite) {
        if (!movingVehicle) return undefined

        const vehicleWidth = movingVehicle.getBoundingClientRect().width || root.current.clientWidth
        const travel = ((root.current.clientWidth + vehicleWidth) / 2) + 28
        gsap.set(root.current, { autoAlpha: 0 })
        gsap.set(brandPrelude, { autoAlpha: 0, scale: 0.94 })
        gsap.set(movingVehicle, { x: -travel, y: 0, scale: 0.72, opacity: 1, filter: 'blur(0.7px)' })
        gsap.set(sideFrame, { opacity: 1 })
        gsap.set(confirmation, { opacity: 0 })
        gsap.set(confirmationRule, { scaleX: 0, transformOrigin: 'center' })
        const timeline = gsap.timeline()
          .to(root.current, { autoAlpha: 1, duration: 0.18, ease: 'power2.out' })
          .to(brandPrelude, { autoAlpha: 1, scale: 1, duration: 0.34, ease: 'power2.out' })
          .to(brandPrelude, { autoAlpha: 0, duration: 0.2, ease: 'power2.in' }, '+=0.22')
          .to(movingVehicle, { x: -8, scale: 0.82, filter: 'blur(0)', duration: 0.92, ease: 'power2.out' })
          .to(movingVehicle, { x: travel, scale: 0.88, duration: 0.82, ease: 'power2.in' }, '+=0.08')
          .to(confirmation, { opacity: 1, duration: 0.22, ease: 'power2.out' })
          .to(confirmationRule, { scaleX: 1, duration: 0.24, ease: 'power2.out' }, '<')
          .to({}, { duration: 0.34 })
          .to(root.current, { autoAlpha: 0, duration: 0.2, ease: 'power2.in' })
          .call(onComplete)
        return () => timeline.kill()
      }

      if (!movingVehicle) return undefined

      gsap.set(root.current, { autoAlpha: 0 })
      // Xe vào từ TRÁI và chạy sang phải (mũi xe hướng phải — xem ghi chú đầu file).
      const enterX = -((root.current.clientWidth + movingVehicle.offsetWidth) / 2 + 48)
      // Điểm tụ của cú lùi cuối: chéo LÊN và SANG PHẢI, không phải giữa khung.
      //
      // Khung `spin-3` vốn đã là "đuôi xe quay về người xem, thân lùi chéo sang PHẢI" (xem ghi
      // chú đầu file). Bản trước cho xe thu nhỏ tại x: 0 — tức thân xe chỉ sang phải còn quỹ đạo
      // lại đi thẳng vào giữa. Hai thứ đá nhau nên mắt đọc thành "xe bị hút vào" chứ không phải
      // "xe đang chạy đi". Cho điểm tụ trùng với hướng thân xe thì cú chạy mới thật.
      //
      // Đi kèm chiều LÊN vì vật ở xa luôn nằm cao hơn trong khung: cùng lúc nhỏ đi và dâng lên
      // là cách mắt người nhận ra khoảng cách. X tính theo % bề ngang rồi chặn trần để màn rộng
      // không quăng xe đi quá xa, màn hẹp không bị cụt.
      //
      // Y buộc theo X chứ KHÔNG theo chiều cao khung. Tính theo chiều cao thì tỷ lệ hai trục đổi
      // theo từng khổ màn hình: đo thử ở khung 1100×460 ra góc chỉ ~10°, nhìn thành xe chạy ngang
      // chứ không phải chạy xa. Buộc theo X thì góc chéo luôn cố định ~23° trên mọi màn hình.
      const retreatX = Math.min(root.current.clientWidth * 0.22, 320)
      const retreatY = -retreatX * 0.42
      gsap.set(movingVehicle, { x: enterX, y: 0, scale: 0.7, rotateZ: 0.18, opacity: 1, filter: 'blur(1.4px)' })
      gsap.set(sideFrame, { opacity: 1 })
      gsap.set(rearFrame, { opacity: 0 })
      gsap.set(brandPrelude, { autoAlpha: 0, scale: 0.82 })
      gsap.set(airLines, { scaleX: 0.08, opacity: 0, transformOrigin: 'right center' })
      gsap.set(confirmation, { opacity: 0 })

      const timeline = gsap.timeline({ defaults: { ease: 'power3.inOut' } })
      timeline
        // Giao diện tắt hẳn vào nền đen, chữ VinFast hiện chính diện rồi rời sân khấu
        // trước khi xe vào. Chữ không bao giờ xoay hay lật.
        .call(() => { root.current.dataset.phase = 'blackout' })
        .to(root.current, { autoAlpha: 1, duration: 0.3, ease: 'power2.out' })
        .call(() => { root.current.dataset.phase = 'brand-prelude' })
        .to(brandPrelude, { autoAlpha: 1, scale: 1, duration: 0.54, ease: 'power3.out' })
        .to({}, { duration: 0.72 })
        .to(brandPrelude, { autoAlpha: 0, scale: 0.96, filter: 'blur(5px)', duration: 0.36, ease: 'power2.in' })
        .set(brandPrelude, { visibility: 'hidden' })
        .addLabel('vehicle-approach')
        // Hông xe lướt vào, tăng tốc dần. Vệt gió gắn đúng vào quãng này và tắt trước khi drift.
        .call(() => { root.current.dataset.phase = 'side-approach' })
        .to(movingVehicle, { x: -132, scale: 0.76, filter: 'blur(0.55px)', duration: 1.48, ease: 'power2.in' })
        .to(movingVehicle, { x: 0, scale: 0.79, filter: 'blur(0)', duration: 0.48, ease: 'power3.out' })
        .to(air, { opacity: 1, duration: 0.12 }, 'vehicle-approach+=0.06')
        .to(airLines, { scaleX: 1, opacity: 0.42, duration: 0.62, stagger: 0.055, ease: 'power2.in' }, 'vehicle-approach+=0.1')
        .to(airLines, { scaleX: 0.2, opacity: 0, duration: 0.5, stagger: 0.035, ease: 'power3.out' }, 'vehicle-approach+=1.1')
        .to(air, { opacity: 0, duration: 0.2 }, 'vehicle-approach+=1.62')
        // Trọng lượng dồn về trước, rồi xe xoay đuôi về phía người xem. Khói lốp và vệt phanh
        // bắt đầu đúng lúc tải trọng đạt đỉnh. Cú xoay = chồng mờ hai khung 360 thật, kèm một
        // chút rotateY để mắt đọc ra đây là chuyển động xoay chứ không phải ảnh nhảy.
        .call(() => { root.current.dataset.phase = 'drift' })
        .to(movingVehicle, { x: 44, y: 14, rotateZ: -1.25, scaleX: 1.018, scaleY: 0.982, duration: 0.28, ease: 'power2.out' })
        .to(smoke.current, { intensity: 1, skid: 1, duration: 0.16, ease: 'power2.out' }, '<')
        .to(sideFrame, { opacity: 0, duration: 0.66, ease: 'power2.inOut' }, '<')
        .to(rearFrame, { opacity: 1, duration: 0.66, ease: 'power2.inOut' }, '<')
        .fromTo(movingVehicle, { rotateY: 0 }, { rotateY: 13, duration: 0.66, ease: 'power2.inOut' }, '<')
        .to(movingVehicle, { rotateY: 0, duration: 0.5, ease: 'power2.out' }, '>')
        .to(smoke.current, { rearMix: 1, duration: 0.82, ease: 'power1.inOut' }, '<-=0.52')
        .to(movingVehicle, { x: 0, y: 0, rotateZ: 0, scaleX: 1, scaleY: 1, duration: 0.86, ease: 'power3.out' }, '<+=0.18')
        .to(smoke.current, { intensity: 0, skid: 0, duration: 0.92, ease: 'power2.out' }, '<+=0.24')
        .to({}, { duration: 0.38 })
        // Xe lùi xa theo đúng hướng thân nó đang chỉ: chéo lên góc phải. Vẫn nét trong lúc lao
        // vào chiều sâu; chỉ mờ đi ở mét cuối.
        .call(() => { root.current.dataset.phase = 'rear-retreat' })
        .to(movingVehicle, { x: retreatX, y: retreatY, scale: 0.055, duration: 1.72, ease: 'expo.in' })
        .to(movingVehicle, { opacity: 0, duration: 0.28, ease: 'power1.in' }, '-=0.22')
        .to(canvas.current, { opacity: 0, duration: 0.38 }, '-=0.34')
        .call(() => { root.current.dataset.phase = 'confirmed' })
        .to(confirmation, { opacity: 1, duration: 0.42, ease: 'power2.out' })
        .to(confirmationRule, { scaleX: 1, duration: 0.49, ease: 'power3.out' }, '<+=0.04')
        .to({}, { duration: 0.52 })
        .to(confirmation, { opacity: 0, y: -8, duration: 0.3, ease: 'power2.in' })
        .to(root.current, { autoAlpha: 0, duration: 0.42, ease: 'power2.inOut' })
        .call(onComplete)

      return () => timeline.kill()
    },
    { scope: root, dependencies: [framesReady, mobileLite, onComplete] },
  )

  if (!car) return null

  return (
    <div className="booking-film" ref={setRootNode} role="dialog" aria-modal="true" aria-label="Lịch lái thử đã được xác nhận" tabIndex={-1}>
      <button type="button" className="booking-film__skip" onClick={onComplete} autoFocus>
        Bỏ qua chuyển động
      </button>
      <div className="booking-film__brand" aria-hidden="true">
        <img className="booking-film__brand-mark" src={vinfastWordmark} alt="" />
      </div>
      <div className="booking-film__air" aria-hidden="true"><span /><span /><span /><span /></div>
      {!mobileLite && <canvas className="booking-film__smoke" ref={canvas} aria-hidden="true" />}
      <div className="booking-film__rig">
        {/* Hai khung chồng lên nhau, chỉ đổi opacity nên trình duyệt không phải tính lại bố cục. */}
        <div className="booking-film__vehicle" ref={vehicle}>
          <img className="booking-film__frame" data-frame="side" src={lacHongSideFrame} alt="" aria-hidden="true" />
          {!mobileLite && <img className="booking-film__frame" data-frame="rear" src={lacHongRearFrame} alt="" aria-hidden="true" />}
        </div>
      </div>
      <div className="booking-film__confirmation" aria-hidden="true">
        <i />
        <strong>Lịch lái thử đã được xác nhận.</strong>
      </div>
    </div>
  )
}
