/**
 * api/booking.js — Toàn bộ lệnh đặt lịch lái thử gửi lên backend, gồm cả tin nhắn cho ViVi.
 *
 * Điểm quan trọng: TẤT CẢ thao tác đặt lịch đều đi qua MỘT endpoint duy nhất
 * POST /api/v1/chat của LangGraph Agent, phân biệt nhau bằng trường `action`.
 * Có `action` thì backend gọi thẳng tool và BỎ QUA LLM — nên luồng đặt lịch vẫn chạy
 * bình thường dù chưa có OpenAI key. Chỉ chat tự do (sendBookingMessage) mới cần key.
 *
 * Nhóm 1 — đặt lịch mới (qua /chat):
 * - sendBookingMessage(): người dùng gõ tin nhắn tự do cho ViVi.
 * - searchBookingOptions(): tìm showroom có đúng mẫu xe + khung giờ trống (theo địa chỉ hoặc GPS).
 * - holdBookingSlot(): giữ chỗ một khung giờ (backend trả hạn giữ, UI đếm ngược).
 * - saveBookingCustomer(): lưu tên/email bắt buộc và số điện thoại nếu có.
 * - confirmHeldBooking(): chốt đặt lịch, trả về mã lịch.
 *
 * Nhóm 2 — tra cứu/sửa/huỷ lịch đã đặt (qua POST /api/v1/demo/action):
 * - requestBookingAccess() → verifyBookingAccess(): xin và xác thực OTP gửi qua email.
 * - getVerifiedBooking() · updateVerifiedBooking() · cancelVerifiedBooking().
 * - holdVerifiedReschedule() → confirmVerifiedReschedule(): đổi sang khung giờ khác.
 *
 * conversation_id được giữ trong sessionStorage để ViVi nhớ mạch hội thoại trong cùng tab.
 */
import { ApiError, apiGet, apiPost } from './client'
import { actionId } from './ids'

const CONVERSATION_KEY = 'vinfast:booking-conversation-id'
const PUBLIC_ACTION_ERROR_MESSAGES = {
  SLOT_NO_LONGER_AVAILABLE: 'Khung giờ này đã qua hoặc không còn khả dụng, vui lòng chọn giờ khác.',
  SLOT_UNAVAILABLE: 'Khung giờ này không còn khả dụng, vui lòng chọn giờ khác.',
  HOLD_EXPIRED: 'Thời gian giữ chỗ đã hết hạn, vui lòng chọn lại khung giờ.',
  VEHICLE_NOT_READY: 'Xe demo hiện không sẵn sàng cho khung giờ này, vui lòng chọn lịch khác.',
  VERSION_CONFLICT: 'Thông tin đặt lịch đã thay đổi, vui lòng tải lại và thử lại.',
  INVALID_INPUT: 'Thông tin gửi lên chưa hợp lệ, vui lòng kiểm tra lại.',
  SERVICE_TEMPORARILY_UNAVAILABLE: 'ViVi đang tạm thời chưa thể xử lý yêu cầu này. Quý khách vui lòng thử lại sau.',
  AGENT_ACTION_FAILED: 'Thao tác giữ chỗ chưa hoàn tất. Vui lòng chọn lại khung giờ.',
}

const readConversationId = () => {
  if (typeof window === 'undefined') return ''
  return window.sessionStorage.getItem(CONVERSATION_KEY) || ''
}

const rememberConversationId = (conversationId) => {
  if (typeof window !== 'undefined' && conversationId) {
    window.sessionStorage.setItem(CONVERSATION_KEY, conversationId)
  }
}

const compactObject = (value) => Object.fromEntries(
  Object.entries(value).filter(([, item]) => item !== '' && item !== null && item !== undefined),
)

const VEHICLE_CONTEXT_STAGES = new Set([
  'need_address', 'need_ward', 'choose_showroom', 'choose_slot', 'collect_info', 'review', 'success',
])
const SHOWROOM_CONTEXT_STAGES = new Set(['choose_slot', 'collect_info', 'review', 'success'])
const SLOT_CONTEXT_STAGES = new Set(['collect_info', 'review', 'success'])
const NEARBY_SHOWROOM_CONTEXT_STAGES = new Set(['choose_showroom', 'choose_slot'])

const normalizeAgentContext = (context = {}) => {
  const normalized = { channel: 'booking' }
  const stage = String(context.stage || '').trim()
  const recipient = String(context.recipient || '').trim()

  if (stage) normalized.stage = stage
  if (recipient) normalized.recipient = recipient

  if (context.selectedVehicle && VEHICLE_CONTEXT_STAGES.has(stage)) {
    normalized.selectedVehicle = compactObject({
      id: context.selectedVehicle.id,
      name: context.selectedVehicle.name,
    })
  }
  if (context.selectedShowroom && SHOWROOM_CONTEXT_STAGES.has(stage)) {
    normalized.selectedShowroom = compactObject({
      id: context.selectedShowroom.id,
      name: context.selectedShowroom.name,
    })
  }
  if (context.selectedSlot && SLOT_CONTEXT_STAGES.has(stage)) {
    normalized.selectedSlot = compactObject({
      slotId: context.selectedSlot.slotId,
      time: context.selectedSlot.time,
      dateLabel: context.selectedSlot.dateLabel,
      isAvailable: context.selectedSlot.isAvailable,
      unavailableLabel: context.selectedSlot.unavailableLabel,
    })
  }
  if (
    NEARBY_SHOWROOM_CONTEXT_STAGES.has(stage)
    && Array.isArray(context.nearbyShowrooms)
    && context.nearbyShowrooms.length
  ) {
    normalized.nearbyShowrooms = context.nearbyShowrooms.slice(0, 10).map((showroom) => compactObject({
      id: showroom.id,
      name: showroom.name,
      address: showroom.address,
      distance: showroom.distance,
    }))
  }
  if (context.userLocation && NEARBY_SHOWROOM_CONTEXT_STAGES.has(stage)) {
    normalized.userLocation = compactObject({
      latitude: context.userLocation.latitude,
      longitude: context.userLocation.longitude,
    })
  }
  if (context.bookingId) normalized.bookingId = String(context.bookingId)
  if (context.pendingReschedule) {
    normalized.pendingReschedule = compactObject({
      reschedule_date_type: context.pendingReschedule.reschedule_date_type,
      reschedule_target_date: context.pendingReschedule.reschedule_target_date,
      reschedule_day_offset: context.pendingReschedule.reschedule_day_offset,
      reschedule_target_time: context.pendingReschedule.reschedule_target_time,
    })
  }

  return normalized
}

const agentRequest = async ({ message, action, actionPayload = {}, context = {} }) => {
  const result = await apiPost('/chat', {
    message,
    conversation_id: readConversationId(),
    ...(action ? { action } : {}),
    action_payload: actionPayload,
    context: normalizeAgentContext(context),
  })
  rememberConversationId(result.conversation_id)
  return result
}

const agentAction = async (action, message, actionPayload) => {
  const result = await agentRequest({ message, action, actionPayload })
  if (result.action_error || result.action_data == null) {
    const code = result.action_error || 'AGENT_ACTION_FAILED'
    throw new ApiError(PUBLIC_ACTION_ERROR_MESSAGES[code] || result.response || PUBLIC_ACTION_ERROR_MESSAGES.AGENT_ACTION_FAILED, {
      code,
      retryable: true,
    })
  }
  return result.action_data
}

export const sendBookingMessage = (message, context = {}) => agentRequest({ message, context })

// Uses the existing /chat endpoint. The invitation stays outside agent context.
const driverChatRequest = ({ message, conversationId = '', invitationToken }) => apiPost('/chat', {
  message,
  conversation_id: conversationId,
  driver_invitation_token: invitationToken,
  context: { channel: 'driver_invitation' },
})

export const sendDriverChatMessage = (message, { conversationId, invitationToken }) => driverChatRequest({
  message,
  conversationId,
  invitationToken,
})

export const getDriverInvitationContext = (invitationToken) => apiGet(
  `/driver-chat/${encodeURIComponent(invitationToken)}/context`,
  { cacheKey: `driver-invitation:${invitationToken}`, fallbackToCache: false },
)

export const resetBookingConversation = () => {
  if (typeof window !== 'undefined') window.sessionStorage.removeItem(CONVERSATION_KEY)
}

export const getFloatingDemoCapabilities = () => apiGet('/floating-demo/capabilities', {
  cacheKey: 'floating-demo-capabilities',
  fallbackToCache: false,
})

export const searchFloatingDemoOptions = async ({ vehicleModel, showroomId = '', showroomQuery = '', showroomLimit = 12, latitude, longitude }) => {
  try {
    return await apiPost('/floating-demo/options', {
      vehicle_model: vehicleModel,
      showroom_id: showroomId,
      showroom_query: showroomQuery,
      showroom_limit: showroomLimit,
      ...(latitude === undefined ? {} : { latitude }),
      ...(longitude === undefined ? {} : { longitude }),
    })
  } catch (error) {
    // Preserve explicit backend errors (especially FLOATING_DEMO_DISABLED).
    // Only an unclassified 404 indicates that the route may be missing.
    if (error.status === 404 && error.code === 'NETWORK_ERROR') {
      throw new ApiError('Không tìm thấy API chọn lịch demo. Hãy kiểm tra địa chỉ API và triển khai backend mới nhất.', {
        code: 'FLOATING_DEMO_API_OUTDATED', status: 404, retryable: false,
      })
    }
    throw error
  }
}

export const searchBookingOptions = ({ vehicleModel, showroomId, showroomQuery, address, latitude, longitude, preferredDate, preferredDates, preferredDateFrom, preferredDateTo, preferredTime, showroomLimit = 5, slotLimit }) => agentAction(
  'search_options',
  showroomId
    ? `Kiểm tra lịch trống cho ${vehicleModel} tại showroom đã chọn.`
    : showroomQuery
      ? `Tìm showroom ${showroomQuery} có ${vehicleModel}.`
    : address
      ? `Tìm showroom có ${vehicleModel} gần địa chỉ ${address}.`
      : latitude && longitude
        ? `Tìm showroom có ${vehicleModel} gần tọa độ GPS.`
        : `Tìm các khu vực có showroom lái thử ${vehicleModel}.`,
  {
    vehicle_model: vehicleModel,
    showroom_id: showroomId,
    showroom_query: showroomQuery,
    address,
    latitude,
    longitude,
    preferred_date: preferredDate,
    preferred_dates: preferredDates,
    preferred_date_from: preferredDateFrom,
    preferred_date_to: preferredDateTo,
    preferred_time: preferredTime,
    showroom_limit: showroomLimit,
    ...(slotLimit === undefined ? {} : { slot_limit: slotLimit }),
  },
)

// Read the complete calendar without adding a synthetic turn to chat history
// or calling the LLM. The same backend search validation still applies.
export const searchBookingCalendar = ({ vehicleModel, showroomId }) => apiPost('/test-drive/actions', {
  action: 'search_options',
  payload: { vehicle_model: vehicleModel, showroom_id: showroomId },
})

export const holdBookingSlot = (slotId, uiActionId = actionId('hold')) => agentAction(
  'hold_slot',
  'Tôi xác nhận chọn khung giờ này. Hãy giữ chỗ giúp tôi.',
  {
    slot_id: slotId,
    ui_action_id: uiActionId,
  },
)



/**
 * Lưu thông tin người đặt và người lái vào draft.
 *
 * Người lái có thể có ĐẦU MỐI LIÊN HỆ RIÊNG. Trước đây `driver_patch` bị gán lại đúng
 * `person.phone` / `person.email` của người đặt, nên đặt hộ thì showroom chỉ có số của
 * người đặt — gọi nhầm người, và người thật sự cầm lái không nhận được thông báo nào.
 * Đã kiểm chứng 16/08/2026: backend nhận email/SĐT khác nhau và tạo HAI bản ghi person.
 *
 * `person.driverSameContact` = true nghĩa là người lái dùng chung liên hệ với người đặt —
 * khi đó vẫn gửi liên hệ của người đặt, nhưng là do người dùng CHỌN thế, không phải do
 * frontend tự áp đặt.
 */
export const saveBookingCustomer = ({ bookingId, version, recipient, person }) => {
  const shareContact = recipient === 'self' || person.driverSameContact !== false

  return agentAction(
    'update_draft',
    'Tôi đã hoàn tất thông tin người đặt và người lái.',
    {
      booking_id: bookingId,
      expected_version: version,
      booker_patch: {
        full_name: person.bookingName,
        phone: person.phone,
        email: person.email,
      },
      driver_same_as_booker: recipient === 'self',
      driver_patch: recipient === 'other'
        ? {
            full_name: person.driverName,
            phone: shareContact ? person.phone : person.driverPhone,
            email: shareContact ? person.email : person.driverEmail,
          }
        : null,
      has_valid_license_commitment: person.hasLicense,
    },
  )
}

export const confirmHeldBooking = ({ bookingId, version, uiActionId = actionId('confirm') }) => agentAction(
  'confirm_booking',
  'Tôi đã kiểm tra thông tin và xác nhận đặt lịch lái thử.',
  {
    booking_id: bookingId,
    expected_version: version,
    ui_action_id: uiActionId,
  },
)

const bookingManagementAction = async (action, payload) => {
  const result = await apiPost('/test-drive/actions', { action, payload })
  return result
}

export const releaseBookingHold = (bookingId) => bookingManagementAction(
  'release_hold',
  { booking_id: bookingId },
)



export const requestBookingAccess = ({ bookingCode = '', email = '', contactValue = '', purpose = 'lookup' }) => bookingManagementAction('request_access', {
  ...((bookingCode || '').trim() ? { booking_code: (bookingCode || '').trim() } : {}),
  contact_value: email || contactValue || '',
  purpose,
  preferred_channel: 'email',
})

export const verifyBookingAccess = ({ challengeId, otpCode }) => bookingManagementAction('verify_access', {
  challenge_id: challengeId,
  otp_code: otpCode,
})

export const getVerifiedBooking = ({ accessToken, bookingCode, bookingId }) => bookingManagementAction('get_details', {
  access_session_token: accessToken,
  ...(bookingId ? { booking_id: bookingId } : { booking_code: bookingCode }),
})

export const listVerifiedBookings = ({ accessToken }) => bookingManagementAction('list_bookings', {
  access_session_token: accessToken,
})

export const updateVerifiedBooking = ({ bookingId, accessToken, bookerPatch, driverPatch, driverSameAsBooker }) => bookingManagementAction('update_details', {
  booking_id: bookingId,
  access_session_token: accessToken,
  booker_patch: bookerPatch,
  driver_patch: driverPatch,
  driver_same_as_booker: driverSameAsBooker,
})

export const cancelVerifiedBooking = ({ bookingId, accessToken, reason = '' }) => bookingManagementAction('cancel_booking', {
  booking_id: bookingId,
  access_session_token: accessToken,
  ui_action_id: actionId('cancel'),
  reason,
})

export const searchVerifiedReschedule = ({ bookingId, accessToken, intent }) => bookingManagementAction('search_reschedule', {
  current_booking_id: bookingId,
  access_session_token: accessToken,
  date_type: intent?.reschedule_date_type || null,
  target_date: intent?.reschedule_target_date || null,
  day_offset: intent?.reschedule_day_offset ?? null,
  target_time: intent?.reschedule_target_time || null,
})

export const holdVerifiedReschedule = ({ bookingId, slotId, accessToken }) => bookingManagementAction('hold_reschedule', {
  current_booking_id: bookingId,
  new_slot_id: slotId,
  access_session_token: accessToken,
  ui_action_id: actionId('reschedule-hold'),
})

export const confirmVerifiedReschedule = ({ bookingId, newBookingId, accessToken }) => bookingManagementAction('confirm_reschedule', {
  current_booking_id: bookingId,
  new_booking_id: newBookingId,
  access_session_token: accessToken,
  ui_action_id: actionId('reschedule-confirm'),
})
