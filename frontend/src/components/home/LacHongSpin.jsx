/**
 * Một bề mặt canvas duy nhất cho trải nghiệm xoay Lạc Hồng.
 *
 * Nguồn hiện chưa có GLB/GLTF, nên canvas nội suy 5 góc render đã được tách alpha.
 * Không render thumbnail, không autoplay và không để lộ từng lớp ảnh trong DOM. Khi backend
 * cung cấp model 3D thật, có thể thay canvas này bằng model-viewer mà không đổi bố cục ngoài.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { HandPointing, SpinnerGap } from '@phosphor-icons/react'

const DRAG_PER_FRAME = 150

const normalizedPosition = (value, total) => ((value % total) + total) % total

// Các frame nguồn có kích thước và khoảng alpha khác nhau. Đo silhouette một lần khi tải
// để luôn căn theo thân xe thật, không căn theo phần canvas trong suốt khiến xe bị lệch.
const measureVisibleBounds = (image) => {
  const sampleScale = Math.min(1, 640 / image.naturalWidth)
  const width = Math.max(1, Math.round(image.naturalWidth * sampleScale))
  const height = Math.max(1, Math.round(image.naturalHeight * sampleScale))
  const sample = document.createElement('canvas')
  sample.width = width
  sample.height = height
  const context = sample.getContext('2d', { willReadFrequently: true })
  context.drawImage(image, 0, 0, width, height)
  const pixels = context.getImageData(0, 0, width, height).data
  let minX = width
  let minY = height
  let maxX = 0
  let maxY = 0

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (pixels[(y * width + x) * 4 + 3] < 12) continue
      minX = Math.min(minX, x)
      minY = Math.min(minY, y)
      maxX = Math.max(maxX, x)
      maxY = Math.max(maxY, y)
    }
  }

  if (minX > maxX || minY > maxY) {
    return { x: 0, y: 0, width: image.naturalWidth, height: image.naturalHeight }
  }

  return {
    x: minX / sampleScale,
    y: minY / sampleScale,
    width: (maxX - minX + 1) / sampleScale,
    height: (maxY - minY + 1) / sampleScale,
  }
}

export function LacHongSpin({ frames, name }) {
  const canvasRef = useRef(null)
  const imagesRef = useRef([])
  const positionRef = useRef(0)
  const dragRef = useRef(null)
  const paintFrameRef = useRef(0)
  const [ready, setReady] = useState(false)
  const [failed, setFailed] = useState(false)
  const [touched, setTouched] = useState(false)

  const paint = useCallback(() => {
    const canvas = canvasRef.current
    const framesWithBounds = imagesRef.current
    if (!canvas || framesWithBounds.length !== frames.length) return

    const bounds = canvas.getBoundingClientRect()
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const width = Math.max(1, Math.round(bounds.width))
    const height = Math.max(1, Math.round(bounds.height))

    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
    }

    const context = canvas.getContext('2d')
    context.setTransform(dpr, 0, 0, dpr, 0, 0)
    context.clearRect(0, 0, width, height)

    const ambience = context.createRadialGradient(
      width * 0.52,
      height * 0.45,
      width * 0.04,
      width * 0.52,
      height * 0.45,
      width * 0.72,
    )
    ambience.addColorStop(0, '#273039')
    ambience.addColorStop(0.48, '#141a20')
    ambience.addColorStop(1, '#080b0f')
    context.fillStyle = ambience
    context.fillRect(0, 0, width, height)

    const floor = context.createRadialGradient(
      width * 0.5,
      height * 0.79,
      0,
      width * 0.5,
      height * 0.79,
      width * 0.38,
    )
    floor.addColorStop(0, 'rgba(0, 0, 0, 0.58)')
    floor.addColorStop(1, 'rgba(0, 0, 0, 0)')
    context.save()
    context.scale(1, 0.24)
    context.fillStyle = floor
    context.fillRect(width * 0.1, height * 2.85, width * 0.8, height)
    context.restore()

    const position = normalizedPosition(positionRef.current, framesWithBounds.length)
    const currentIndex = Math.floor(position)
    const nextIndex = (currentIndex + 1) % framesWithBounds.length
    const rawMix = position - currentIndex
    const mix = rawMix * rawMix * (3 - 2 * rawMix)

    const maxSourceWidth = Math.max(...framesWithBounds.map(({ image }) => image.naturalWidth))
    const maxSourceHeight = Math.max(...framesWithBounds.map(({ image }) => image.naturalHeight))
    const commonScale = Math.min((width * 0.9) / maxSourceWidth, (height * 0.86) / maxSourceHeight)

    const drawImage = ({ image, bounds }, alpha) => {
      const visibleCenterX = bounds.x + bounds.width / 2
      const visibleCenterY = bounds.y + bounds.height / 2
      const x = width * 0.5 - visibleCenterX * commonScale
      // Canh ĐÚNG giữa khung theo chiều dọc. Trước để 0.49 nên xe nhích lên trên
      // khoảng 1% chiều cao khung, đủ để nhìn ra là lệch khi đặt cạnh vòng elip.
      const y = height * 0.5 - visibleCenterY * commonScale
      context.save()
      context.globalAlpha = alpha
      context.drawImage(image, x, y, image.naturalWidth * commonScale, image.naturalHeight * commonScale)
      context.restore()
    }

    drawImage(framesWithBounds[currentIndex], 1 - mix)
    if (mix > 0.001) drawImage(framesWithBounds[nextIndex], mix)
  }, [frames.length])

  const queuePaint = useCallback(() => {
    window.cancelAnimationFrame(paintFrameRef.current)
    paintFrameRef.current = window.requestAnimationFrame(paint)
  }, [paint])

  useEffect(() => {
    let cancelled = false
    const sources = frames.map((src) => new Promise((resolve, reject) => {
      const image = new Image()
      image.decoding = 'async'
      image.onload = () => resolve(image)
      image.onerror = reject
      image.src = src
    }))

    Promise.all(sources).then((images) => {
      if (cancelled) return
      imagesRef.current = images.map((image) => ({ image, bounds: measureVisibleBounds(image) }))
      setFailed(false)
      setReady(true)
      queuePaint()
    }).catch(() => {
      if (!cancelled) {
        setReady(false)
        setFailed(true)
      }
    })

    const observer = new ResizeObserver(queuePaint)
    if (canvasRef.current) observer.observe(canvasRef.current)

    return () => {
      cancelled = true
      observer.disconnect()
      window.cancelAnimationFrame(paintFrameRef.current)
    }
  }, [frames, queuePaint])

  const onPointerDown = (event) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    dragRef.current = { pointerId: event.pointerId, x: event.clientX, position: positionRef.current }
    setTouched(true)
  }

  const onPointerMove = (event) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    positionRef.current = drag.position + (event.clientX - drag.x) / DRAG_PER_FRAME
    queuePaint()
  }

  const endPointer = (event) => {
    if (dragRef.current?.pointerId !== event.pointerId) return
    positionRef.current = Math.round(positionRef.current)
    dragRef.current = null
    queuePaint()
  }

  const onKeyDown = (event) => {
    const step = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0
    if (!step) return
    event.preventDefault()
    positionRef.current = Math.round(positionRef.current) + step
    setTouched(true)
    queuePaint()
  }

  return (
    <div className={`lachong-spin ${ready ? 'is-ready' : failed ? 'is-error' : 'is-loading'}`}>
      <div
        className="lachong-spin__viewport"
        role="img"
        tabIndex={0}
        aria-label={`Góc nhìn xoay của ${name}. Kéo ngang trên xe hoặc dùng phím mũi tên trái phải để xoay.`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endPointer}
        onPointerCancel={endPointer}
        onKeyDown={onKeyDown}
      >
        <canvas ref={canvasRef} className="lachong-spin__canvas" aria-hidden="true" />
        {!ready && !failed && (
          <span className="lachong-spin__loading" aria-live="polite">
            <SpinnerGap size={20} weight="light" />
            Đang dựng góc nhìn
          </span>
        )}
        {failed && (
          <span className="lachong-spin__loading" role="status">
            Góc nhìn tạm thời chưa tải được
          </span>
        )}
        {ready && !touched && (
          <span className="lachong-spin__hint" aria-hidden="true">
            <HandPointing size={18} weight="light" />
            Giữ và kéo trực tiếp trên xe
          </span>
        )}
        <span className="lachong-spin__orbit" aria-hidden="true" />
      </div>
    </div>
  )
}
