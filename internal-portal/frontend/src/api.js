const API_BASE = import.meta.env.VITE_INTERNAL_API_BASE_URL || '/api/v1/internal'

function messageFrom(payload, fallback) {
  return payload?.detail?.message || payload?.message || fallback
}

async function request(path, { token, body, method = 'GET', query } = {}) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) url.searchParams.set(key, value)
  })
  const response = await fetch(url, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (response.status === 204) return null
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(messageFrom(payload, 'Không thể xử lý yêu cầu.'))
    error.code = payload?.detail?.code || 'REQUEST_FAILED'
    error.status = response.status
    throw error
  }
  return payload
}

async function requestText(url, { token } = {}) {
  const response = await fetch(new URL(url, window.location.origin), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(messageFrom(payload, 'Không thể tạo tóm tắt hồ sơ khách hàng.'))
    error.code = payload?.detail?.code || 'REQUEST_FAILED'
    error.status = response.status
    throw error
  }
  return {
    text: await response.text(),
    source: response.headers.get('X-Profile-Summary-Source') || 'generated',
    generatedAt: response.headers.get('X-Profile-Summary-Generated-At') || '',
  }
}

export const api = {
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password } }),
  logout: (token) => request('/auth/logout', { method: 'POST', token }),
  me: (token) => request('/me', { token }),
  users: (token, query) => request('/users', { token, query }),
  createUser: (token, body) => request('/users', { token, method: 'POST', body }),
  updateUser: (token, userId, body) => request(`/users/${userId}`, { token, method: 'PATCH', body }),
  resetUserPassword: (token, userId, password) =>
    request(`/users/${userId}/reset-password`, { token, method: 'POST', body: { password } }),
  revokeUserSessions: (token, userId) =>
    request(`/users/${userId}/revoke-sessions`, { token, method: 'POST' }),
  dashboard: (token) => request('/dashboard', { token }),
  notifications: (token, query) => request('/notifications', { token, query }),
  markNotificationRead: (token, notificationId) =>
    request(`/notifications/${notificationId}/read`, { token, method: 'POST' }),
  markAllNotificationsRead: (token) => request('/notifications/read-all', { token, method: 'POST' }),
  bookings: (token, query) => request('/bookings', { token, query }),
  booking: (token, bookingId) => request(`/bookings/${bookingId}`, { token }),
  profileSummary: (token, bookingId, { refresh = false } = {}) => requestText(
    `${API_BASE}/bookings/${encodeURIComponent(bookingId)}/sales-brief.md${refresh ? '?refresh=true' : ''}`,
    { token },
  ),
  assignBooking: (token, bookingId, staffId) =>
    request(`/bookings/${bookingId}/assignment`, { token, method: 'PUT', body: { staff_id: staffId } }),
  transitionBooking: (token, bookingId, targetStatus, note) =>
    request(`/bookings/${bookingId}/transition`, {
      token,
      method: 'POST',
      body: { target_status: targetStatus, note: note || null },
    }),
  checkLicense: (token, bookingId, body) =>
    request(`/bookings/${bookingId}/license-check`, { token, method: 'POST', body }),
  showrooms: (token) => request('/showrooms', { token }),
  createShowroom: (token, body) => request('/showrooms', { token, method: 'POST', body }),
  updateShowroom: (token, showroomId, body) =>
    request(`/showrooms/${showroomId}`, { token, method: 'PATCH', body }),
  operatingHours: (token, showroomId) => request(`/showrooms/${showroomId}/operating-hours`, { token }),
  updateOperatingHour: (token, showroomId, dayOfWeek, body) =>
    request(`/showrooms/${showroomId}/operating-hours/${dayOfWeek}`, { token, method: 'PUT', body }),
  staff: (token, showroomId) => request('/staff', { token, query: { showroom_id: showroomId } }),
  vehicles: (token, query) => request('/vehicles', {
    token,
    query: typeof query === 'string' ? { showroom_id: query } : query,
  }),
  catalog: (token) => request('/catalog', { token }),
  createVehicleModel: (token, body) => request('/catalog/models', { token, method: 'POST', body }),
  updateVehicleModel: (token, modelId, body) =>
    request(`/catalog/models/${modelId}`, { token, method: 'PATCH', body }),
  createVehicleVariant: (token, body) => request('/catalog/variants', { token, method: 'POST', body }),
  updateVehicleVariant: (token, variantId, body) =>
    request(`/catalog/variants/${variantId}`, { token, method: 'PATCH', body }),
  shifts: (token, query) => request('/shifts', { token, query }),
  createShift: (token, body) => request('/shifts', { token, method: 'POST', body }),
  updateShift: (token, shiftId, body) => request(`/shifts/${shiftId}`, { token, method: 'PATCH', body }),
  unavailability: (token, query) => request('/unavailability', { token, query }),
  createUnavailability: (token, body) => request('/unavailability', { token, method: 'POST', body }),
  updateVehicle: (token, vehicleId, body) => request(`/vehicles/${vehicleId}`, { token, method: 'PATCH', body }),
  transferVehicle: (token, vehicleId, body) =>
    request(`/vehicles/${vehicleId}/transfer`, { token, method: 'POST', body }),
  vehicleTransfers: (token) => request('/vehicle-transfers', { token }),
  vehicleUnavailability: (token, query) => request('/vehicle-unavailability', { token, query }),
  createVehicleUnavailability: (token, vehicleId, body) =>
    request(`/vehicles/${vehicleId}/unavailability`, { token, method: 'POST', body }),
  removeVehicleUnavailability: (token, recordId) =>
    request(`/vehicle-unavailability/${recordId}`, { token, method: 'DELETE' }),
  audit: (token) => request('/audit-events', { token }),
}
