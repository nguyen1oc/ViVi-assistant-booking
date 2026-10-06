import { X } from '@phosphor-icons/react'
import { useDialogFocus } from '../../hooks/useDialogFocus'

export function FactoryFilmDialog({ src, poster, onClose }) {
  const dialogRef = useDialogFocus({ onClose })

  return (
    <div
      ref={dialogRef}
      className="factory-film-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="factory-film-dialog-title"
      tabIndex={-1}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="factory-film-dialog__panel">
        <div className="factory-film-dialog__head">
          <div>
            <span>Tổ hợp sản xuất VinFast</span>
            <h2 id="factory-film-dialog-title">Từ dây chuyền đến chiếc xe hoàn thiện.</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Đóng đoạn phim" autoFocus>
            <X size={24} weight="light" />
          </button>
        </div>
        <div className="factory-film-dialog__media">
          <video src={src} poster={poster} controls autoPlay playsInline preload="metadata" />
        </div>
        <p className="factory-film-dialog__caption">Tổ hợp sản xuất VinFast · Hải Phòng</p>
      </div>
    </div>
  )
}
