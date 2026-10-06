const vietnamDate = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Ho_Chi_Minh', year: 'numeric', month: '2-digit', day: '2-digit',
})
const vietnamTime = new Intl.DateTimeFormat('vi-VN', {
  timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', hour12: false,
})

export const groupSlots = (items) => Object.values(items.reduce((groups, item) => {
  const start = new Date(item.start_at)
  const value = vietnamDate.format(start)
  if (!groups[value]) groups[value] = {
    value,
    dateLabel: new Intl.DateTimeFormat('vi-VN', {
      timeZone: 'Asia/Ho_Chi_Minh', weekday: 'short', day: '2-digit', month: '2-digit',
    }).format(start),
    times: [],
  }
  const end = item.end_at ? new Date(item.end_at) : null
  groups[value].times.push({
    time: vietnamTime.format(start),
    endTime: end ? vietnamTime.format(end) : '',
    durationMinutes: end ? Math.max(0, Math.round((end - start) / 60000)) : 0,
    startAt: item.start_at,
    endAt: item.end_at || '',
    slotId: item.id,
    isAvailable: item.status === 'available',
    unavailableLabel: item.status === 'held' ? 'Đang được giữ' : 'Đã có lịch',
  })
  return groups
}, {}))

// Only merge partial date searches for the same vehicle AND showroom.
// An empty response must also remove stale availability for the requested dates.
export const mergeAvailability = (existing, incoming, { sameSelection, data }) => {
  const dates = new Set(data.requested_dates || [])
  if (data.focused_date) dates.add(data.focused_date.slice(0, 10))
  const range = data.requested_date_range
  if (!sameSelection || (!dates.size && !range)) return incoming
  const retained = existing.filter((day) => !dates.has(day.value)
    && !(range && day.value >= range.from && day.value <= range.to))
  const merged = new Map(retained.map((day) => [day.value, day]))
  for (const day of incoming) merged.set(day.value, day)
  return [...merged.values()].sort((a, b) => a.value.localeCompare(b.value))
}

// A filtered chat answer is not a complete calendar, even when it returns no
// slots. Reload by vehicle + showroom only; never copy chat filters/limits.
export const calendarRequestForSearch = (data, toolInput = {}) => {
  const filtered = Boolean(data.focused_date || data.requested_dates?.length || data.requested_date_range
    || toolInput.preferred_date || toolInput.preferred_dates?.length
    || toolInput.preferred_date_from || toolInput.preferred_date_to || toolInput.slot_limit != null)
  if (!filtered || data.search_stage !== 'slot_selection' || !data.selected_showroom?.id) return null
  const vehicleModel = data.resolved_vehicle?.code || data.resolved_vehicle?.name || toolInput.vehicle_model
  if (!vehicleModel) return null
  return { vehicleModel, showroomId: data.selected_showroom.id }
}

export const heldSlotFromResult = (data) => {
  if (!data?.slot_id || !data.start_at) return null
  const [day] = groupSlots([{ ...data, id: data.slot_id, status: 'held' }])
  return { date: day.value, dateLabel: day.dateLabel, ...day.times[0] }
}
