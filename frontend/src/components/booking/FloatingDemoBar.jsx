import {
  CaretDown,
  CaretLeft,
  CaretRight,
  CaretUp,
  CircleNotch,
  Pause,
  Play,
  X,
} from '@phosphor-icons/react'

const steps = ['Người đặt', 'VF 9', 'Vị trí', 'Showroom', 'Giờ & giữ chỗ', 'Hồ sơ', 'Xác nhận']
const stepDescriptions = [
  'Xác định người đặt lịch lái thử.',
  'Chọn mẫu xe muốn lái thử.',
  'Xác định vị trí để tìm showroom.',
  'Chọn showroom còn lịch phù hợp.',
  'Chọn giờ lái thử và giữ chỗ.',
  'Hoàn thiện hồ sơ người lái thử.',
  'Xác nhận và hoàn tất đặt lịch.',
]
const toolForLog = (text) => {
  const value = String(text || '').toLowerCase()
  if (value.includes('vị trí')) return 'Lấy vị trí'
  if (value.includes('showroom')) return 'Tìm showroom'
  if (value.includes('giờ')) return 'Tìm khung giờ'
  if (value.includes('giữ chỗ')) return 'Giữ chỗ'
  if (value.includes('hồ sơ')) return 'Lưu hồ sơ'
  if (value.includes('xác nhận') || value.includes('đặt lịch thành công')) return 'Xác nhận lịch'
  if (value.includes('dọn lịch')) return 'Dọn lịch demo'
  return 'Điều khiển demo'
}

export function FloatingDemoBar({
  step = 0,
  running = false,
  paused = false,
  busy = false,
  collapsed = false,
  logs = [],
  onAutoPlay,
  onPause,
  onNext,
  onBack,
  onExit,
  onToggle,
}) {
  const primaryAction = running ? onPause : onAutoPlay
  const primaryLabel = running && !paused ? 'Dừng' : paused ? 'Tiếp tục' : 'Chạy demo'
  const primaryIcon = busy ? <CircleNotch size={16} className="is-spinning" /> : running && !paused ? <Pause size={16} /> : <Play size={16} weight="fill" />
  const disableStepControls = busy || (running && !paused)
  const currentStepNumber = Math.min(Math.max(step, 1), steps.length)
  const currentStepDescription = step > 0
    ? stepDescriptions[currentStepNumber - 1]
    : 'Sẵn sàng bắt đầu luồng demo đặt lịch.'

  return (
    <aside className={`floating-demo-bar ${collapsed ? 'is-collapsed' : ''}`} aria-label="Điều khiển demo đặt lịch mô phỏng">
      <div className="floating-demo-bar__controls">
        <button type="button" className="floating-demo-bar__icon-button" onClick={onBack} disabled={disableStepControls || step <= 0} aria-label="Quay lại chặng trước" title="Quay lại chặng trước">
          <CaretLeft size={16} weight="bold" />
        </button>
        <button type="button" className="floating-demo-bar__icon-button" onClick={onNext} disabled={disableStepControls || step >= steps.length} aria-label="Chạy bước tiếp theo" title="Chạy bước tiếp theo">
          <CaretRight size={16} weight="bold" />
        </button>
        <button
          type="button"
          className="floating-demo-bar__toggle"
          onClick={onToggle}
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Mở rộng bảng điều khiển demo' : 'Thu gọn bảng điều khiển demo'}
          title={collapsed ? 'Mở rộng bảng điều khiển demo' : 'Thu gọn bảng điều khiển demo'}
        >
          {collapsed ? <CaretDown size={15} weight="bold" /> : <CaretUp size={15} weight="bold" />}
        </button>
        <button type="button" className="floating-demo-bar__exit" onClick={onExit} disabled={busy} aria-label="Thoát chế độ demo" title="Thoát chế độ demo"><X size={15} weight="bold" /></button>
      </div>
      {collapsed && (
        <div className="floating-demo-bar__compact-actions">
          <button type="button" className="floating-demo-bar__primary floating-demo-bar__primary--compact" onClick={primaryAction} disabled={busy}>
            {primaryIcon}
            <span>{running && !paused ? 'Dừng demo' : paused ? 'Tiếp demo' : 'Chạy demo'}</span>
          </button>
        </div>
      )}

      {!collapsed && (
        <div className="floating-demo-bar__content">
          <div className="floating-demo-bar__head">
            <div>
              <span>Chế độ demo</span>
              <strong>VF 9 · Không tạo lịch thật</strong>
            </div>
          </div>

          <ol className="floating-demo-bar__steps" aria-label="Tiến trình demo">
            {steps.map((label, index) => {
              const number = index + 1
              const complete = step > number
              const active = step === number
              return (
                <li key={label} className={`${complete ? 'is-complete' : ''} ${active ? 'is-active' : ''}`} aria-label={`${number}. ${label}`} title={label}>
                  <span aria-hidden="true">{number}</span>
                </li>
              )
            })}
          </ol>

          <div className="floating-demo-bar__actions">
            <button type="button" className="floating-demo-bar__primary" onClick={primaryAction} disabled={busy} aria-label={primaryLabel} title={primaryLabel}>
              {primaryIcon}
              <span>{primaryLabel}</span>
            </button>
          </div>

          <p className="floating-demo-bar__current-step" aria-live="polite">
            {step > 0 && <strong>Bước {currentStepNumber}/{steps.length}</strong>}
            <span>{currentStepDescription}</span>
          </p>

          <details className="floating-demo-bar__logs">
            <summary>Nhật ký demo <span>{logs.length}</span></summary>
            <ol aria-label="Nhật ký thực thi demo">
              {logs.length ? logs.slice().reverse().map((entry) => (
                <li key={entry.id}><time>{entry.time}</time><span><b>{toolForLog(entry.text)}</b>{entry.text}</span></li>
              )) : <li>Chưa có thao tác nào.</li>}
            </ol>
          </details>
        </div>
      )}
    </aside>
  )
}
