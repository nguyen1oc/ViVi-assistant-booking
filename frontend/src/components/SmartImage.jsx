/**
 * components/SmartImage.jsx — Thẻ ảnh dùng chung, thay cho <img> ở gần như mọi nơi.
 *
 * Tự quản 3 trạng thái và gắn class tương ứng để CSS bắt được:
 * - .smart-image--loading → hiện khung xương xám nhấp nháy (skeleton).
 * - .smart-image--loaded  → ảnh hiện ra.
 * - .smart-image--error   → hiện icon + chữ "Ảnh đang được cập nhật".
 *
 * THẤY CHỮ "Ảnh đang được cập nhật" TRÊN WEB nghĩa là ảnh 404, gần như luôn do
 * backend/data/media chưa được publish. Xem frontend/RUN_LOCAL.md mục 2.
 *
 * Props hữu ích: `fit` (object-fit) · `focalPoint` (giữ tâm ảnh khi crop) ·
 * `aspectRatio` (giữ chỗ trước để trang không bị giật) · `eager` (tải ngay, dùng cho ảnh hero).
 */
import { useState } from 'react'
import { ImageBroken } from '@phosphor-icons/react'

export function SmartImage({
  className = '',
  alt,
  src,
  eager = false,
  fit,
  focalPoint,
  aspectRatio,
  style,
  ...props
}) {
  const [loadedSrc, setLoadedSrc] = useState('')
  const [failedSrc, setFailedSrc] = useState('')
  const status = !src
    ? 'error'
    : failedSrc === src
      ? 'error'
      : loadedSrc === src
        ? 'loaded'
        : 'loading'

  return (
    <span
      className={`smart-image smart-image--${status} ${className}`.trim()}
      style={{ ...style, ...(aspectRatio ? { aspectRatio } : {}) }}
    >
      {status === 'loading' && <span className="smart-image__skeleton" aria-hidden="true" />}
      {status === 'error' && (
        <span className="smart-image__error" role="img" aria-label={`Không tải được ảnh: ${alt}`}>
          <ImageBroken size={28} weight="light" aria-hidden="true" />
          <span>Ảnh đang được cập nhật</span>
        </span>
      )}
      {src && (
        <img
          src={src}
          alt={alt}
          loading={eager ? 'eager' : 'lazy'}
          style={{
            ...(fit ? { objectFit: fit } : {}),
            ...(focalPoint ? { objectPosition: focalPoint } : {}),
          }}
          onLoad={() => {
            setFailedSrc('')
            setLoadedSrc(src)
          }}
          onError={() => {
            setLoadedSrc('')
            setFailedSrc(src)
          }}
          {...props}
        />
      )}
    </span>
  )
}
