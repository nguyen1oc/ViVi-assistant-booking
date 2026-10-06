import { statusLabels } from '../utils.js'

export function StatusBadge({ status }) {
  return <span className={`status status--${status || 'unknown'}`}>{statusLabels[status] || status || '—'}</span>
}
