import { useEffect, useRef } from 'react'

/*
 * Trường hạt của khối ViVi — dựng lại theo bản particle của Google Antigravity
 * (Google Antigravity_files/MainParticlesComponent…js), phần "light theme":
 *
 * - Nền TRẮNG, hạt là CHẤM TRÒN. Bản trước vẽ đoạn thẳng nên nhìn ra thanh dọc,
 *   không phải chấm — đó là lỗi đã sửa ở đây.
 * - Điểm rải theo Poisson-disc (blue noise) như bản gốc, không phải lưới ô vuông:
 *   lưới sẽ lộ hàng lối, blue noise cho mảng hạt đều mà vẫn ngẫu nhiên.
 * - Một "vòng" (ring) chạy quanh khung; hạt nằm trên vành vòng thì to lên, đậm
 *   lên và bị đẩy ra ngoài. Vòng bám con trỏ khi rê chuột, còn lại tự trôi.
 *
 * Chấm trắng thuần trên nền trắng sẽ vô hình, nên chấm nền lấy màu mực rất nhạt
 * (đọc như xám trắng) và chỉ ăn màu xanh VinFast khi vòng quét qua.
 */

const QUIET = [23, 26, 32]
const ACCENT = [44, 100, 237]

function seededRandom(seed) {
  let value = seed >>> 0
  return () => {
    value += 0x6D2B79F5
    let result = value
    result = Math.imul(result ^ (result >>> 15), result | 1)
    result ^= result + Math.imul(result ^ (result >>> 7), result | 61)
    return ((result ^ (result >>> 14)) >>> 0) / 4294967296
  }
}

// Bridson poisson-disc: rải chấm cách nhau tối thiểu minDistance, không thành hàng.
function poissonPoints(width, height, minDistance, random) {
  const cellSize = minDistance / Math.SQRT2
  const cols = Math.max(1, Math.ceil(width / cellSize))
  const rows = Math.max(1, Math.ceil(height / cellSize))
  const grid = new Int32Array(cols * rows).fill(-1)
  const points = []
  const active = []
  const squaredMin = minDistance * minDistance

  const cellIndex = (x, y) => Math.floor(y / cellSize) * cols + Math.floor(x / cellSize)

  const fits = (x, y) => {
    if (x < 0 || y < 0 || x >= width || y >= height) return false
    const column = Math.floor(x / cellSize)
    const row = Math.floor(y / cellSize)
    for (let r = Math.max(0, row - 2); r <= Math.min(rows - 1, row + 2); r += 1) {
      for (let c = Math.max(0, column - 2); c <= Math.min(cols - 1, column + 2); c += 1) {
        const neighbour = grid[r * cols + c]
        if (neighbour === -1) continue
        const dx = points[neighbour].x - x
        const dy = points[neighbour].y - y
        if (dx * dx + dy * dy < squaredMin) return false
      }
    }
    return true
  }

  const insert = (x, y) => {
    grid[cellIndex(x, y)] = points.length
    points.push({ x, y, phase: random() * Math.PI * 2, seed: random(), scale: 0 })
    active.push(points.length - 1)
  }

  insert(width * 0.5, height * 0.5)

  while (active.length) {
    const pick = Math.floor(random() * active.length)
    const parent = points[active[pick]]
    let placed = false

    for (let attempt = 0; attempt < 24; attempt += 1) {
      const angle = random() * Math.PI * 2
      const distance = minDistance * (1 + random())
      const x = parent.x + Math.cos(angle) * distance
      const y = parent.y + Math.sin(angle) * distance
      if (!fits(x, y)) continue
      insert(x, y)
      placed = true
      break
    }

    if (!placed) {
      active[pick] = active[active.length - 1]
      active.pop()
    }
  }

  return points
}

// Nhiễu rẻ tiền thay simplex: đủ mượt để hạt trôi tự nhiên, không tốn CPU.
function wobble(x, y, time) {
  return Math.sin(x * 1.7 + time + Math.cos(y * 1.3 - time * 0.6) * 2.1)
    * Math.cos(y * 1.9 - time * 0.8 + Math.sin(x * 1.1 + time * 0.4) * 1.7)
}

function smoothstep(edge0, edge1, value) {
  if (edge1 === edge0) return value < edge0 ? 0 : 1
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)))
  return t * t * (3 - 2 * t)
}

export function ViViParticleField() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const stage = canvas?.closest('.vivi-journey__stage')
    const context = canvas?.getContext('2d')
    if (!canvas || !stage || !context) return undefined

    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    let reducedMotion = reducedMotionQuery.matches
    let width = 0
    let height = 0
    let points = []
    let animationFrame = 0
    let running = false
    let visible = true
    let hovering = false
    let targetX = 0
    let targetY = 0
    let ringX = 0
    let ringY = 0

    const draw = (time = 0) => {
      context.clearRect(0, 0, width, height)

      const seconds = time * 0.001
      const span = Math.min(width, height)

      if (!hovering) {
        targetX = width * (0.4 + Math.sin(seconds * 0.21) * 0.22)
        targetY = height * (0.5 + Math.cos(seconds * 0.17) * 0.24)
      }

      const easing = hovering ? 0.055 : 0.016
      ringX += (targetX - ringX) * easing
      ringY += (targetY - ringY) * easing

      // Bán kính vòng nhấp nhô bằng hai sóng lệch pha, y như bản gốc.
      const radius = span * (0.34 + Math.sin(seconds * 0.9) * 0.05 + Math.cos(seconds * 2.4) * 0.03)
      const wideBand = span * 0.14
      const tightBand = span * 0.055

      for (let index = 0; index < points.length; index += 1) {
        const point = points[index]
        const noiseX = wobble(point.x * 0.0055, point.y * 0.0055, seconds * 0.35)
        const noiseY = wobble(point.y * 0.0055 + 4.7, point.x * 0.0055 + 1.9, seconds * 0.35)
        const baseX = point.x + noiseX * 5.2 + Math.sin(point.phase + seconds * 0.6) * 1.4
        const baseY = point.y + noiseY * 5.2 + Math.cos(point.phase + seconds * 0.5) * 1.4

        const deltaX = baseX - ringX
        const deltaY = baseY - ringY
        const distance = Math.max(1, Math.hypot(deltaX, deltaY))

        const wide = smoothstep(radius - wideBand * 2, radius, distance)
          - smoothstep(radius, radius + wideBand, distance)
        const tight = smoothstep(radius - tightBand * 2, radius, distance)
          - smoothstep(radius, radius + tightBand, distance)
        const inner = smoothstep(radius + tightBand, radius, distance) * 0.22

        let target = wide * wide + Math.pow(tight, 3) * 2.6 + inner
        target += (point.seed - 0.5) * 0.12 * (wide + inner)
        target = Math.min(1, Math.max(0, target))

        point.scale += (target - point.scale) * 0.16
        const strength = point.scale

        const push = Math.pow(Math.max(0, tight), 0.75) * span * 0.05
        const x = baseX + (deltaX / distance) * push
        const y = baseY + (deltaY / distance) * push

        // Cỡ chấm quy từ shader gốc: gl_PointSize = vScale * 7 * (pixelRatio * 0.5)
        // * (bềRộng / 2000 * 0.75). Với khung ~1400px ra đường kính ≈ vScale * 1,84 CSS px,
        // tức hạt nền chưa tới 1px và hạt trên vành khoảng 5–6px. Bản trước to gấp rưỡi.
        // Chấm nhỏ thì mờ, nên bù lại bằng độ đậm nền cao hơn một chút.
        const dotRadius = 0.45 + strength * 2.35
        const alpha = 0.18 + strength * 0.7
        const red = Math.round(QUIET[0] + (ACCENT[0] - QUIET[0]) * strength)
        const green = Math.round(QUIET[1] + (ACCENT[1] - QUIET[1]) * strength)
        const blue = Math.round(QUIET[2] + (ACCENT[2] - QUIET[2]) * strength)

        context.beginPath()
        context.arc(x, y, dotRadius, 0, Math.PI * 2)
        context.fillStyle = `rgba(${red}, ${green}, ${blue}, ${alpha})`
        context.fill()
      }
    }

    const loop = (time) => {
      if (!running) return
      draw(time)
      animationFrame = window.requestAnimationFrame(loop)
    }

    const start = () => {
      if (running || reducedMotion || !visible) return
      running = true
      animationFrame = window.requestAnimationFrame(loop)
    }

    const stop = () => {
      running = false
      window.cancelAnimationFrame(animationFrame)
    }

    const resize = () => {
      const rect = stage.getBoundingClientRect()
      width = Math.max(1, Math.round(rect.width))
      height = Math.max(1, Math.round(rect.height))
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.round(width * pixelRatio)
      canvas.height = Math.round(height * pixelRatio)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

      // Giãn cách cũng theo bản gốc: khoảng 24 hàng hạt trên chiều cao khung hình.
      const minDistance = width < 720 ? 26 : 24
      const random = seededRandom(Math.round(width * 13 + height * 17) || 1)
      points = poissonPoints(width, height, minDistance, random)
      targetX = ringX = width * 0.4
      targetY = ringY = height * 0.5
      draw(performance.now())
    }

    const handlePointerMove = (event) => {
      if (event.pointerType === 'touch') return
      const rect = stage.getBoundingClientRect()
      targetX = event.clientX - rect.left
      targetY = event.clientY - rect.top
      hovering = true
    }

    const handlePointerLeave = () => {
      hovering = false
    }

    const handleMotionPreference = (event) => {
      reducedMotion = event.matches
      if (reducedMotion) {
        stop()
        hovering = false
        draw(performance.now())
      } else {
        start()
      }
    }

    const resizeObserver = new ResizeObserver(resize)
    const intersectionObserver = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
      if (visible) start()
      else stop()
    }, { rootMargin: '160px 0px' })

    resizeObserver.observe(stage)
    intersectionObserver.observe(stage)
    stage.addEventListener('pointermove', handlePointerMove, { passive: true })
    stage.addEventListener('pointerleave', handlePointerLeave)
    reducedMotionQuery.addEventListener('change', handleMotionPreference)
    resize()
    start()

    return () => {
      stop()
      resizeObserver.disconnect()
      intersectionObserver.disconnect()
      stage.removeEventListener('pointermove', handlePointerMove)
      stage.removeEventListener('pointerleave', handlePointerLeave)
      reducedMotionQuery.removeEventListener('change', handleMotionPreference)
    }
  }, [])

  return (
    <div className="vivi-particles" aria-hidden="true">
      <canvas ref={canvasRef} className="vivi-particles__canvas" />
    </div>
  )
}
