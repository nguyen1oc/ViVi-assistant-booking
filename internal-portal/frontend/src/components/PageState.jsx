import { CircleNotch, WarningCircle } from '@phosphor-icons/react'

export function PageState({ loading, error, children }) {
  if (loading) {
    return (
      <div className="page-state">
        <CircleNotch className="spin" size={25} />
        <span>Đang đồng bộ dữ liệu vận hành…</span>
      </div>
    )
  }
  if (error) {
    return (
      <div className="page-state page-state--error">
        <WarningCircle size={24} />
        <span>{error}</span>
      </div>
    )
  }
  return children
}
