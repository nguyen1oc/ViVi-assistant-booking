/**
 * pages/BookingPage.jsx — TRANG ĐẶT LỊCH LÁI THỬ tại /booking. File lớn nhất dự án (~1800 dòng).
 *
 * Đây là trái tim của sản phẩm: khung chat ViVi bên phải, không gian làm việc bên trái,
 * và một máy trạng thái (state machine) điều khiển toàn bộ luồng.
 *
 * ══ LUỒNG 9 BƯỚC (biến `stage`) ══
 *  idle → chọn đặt cho ai (RecipientModal)  ·  need_car → chọn mẫu xe
 *  need_address / need_ward → nhập địa chỉ hoặc bấm lấy GPS
 *  choose_showroom → chọn showroom trên bản đồ  ·  choose_slot → chọn khung giờ
 *  collect_info → điền thông tin  ·  review → xem lại phiếu  ·  success → đặt xong, có mã lịch
 *  Ngoài luồng chính còn nhánh 'lookup' để tra cứu/sửa/huỷ lịch cũ bằng OTP.
 *  Vào từ /booking?car=vf9 thì bỏ qua bước chọn xe.
 *
 * ══ 3 TAB CỦA KHÔNG GIAN LÀM VIỆC (biến `activeView`) ══
 *  'car' Mẫu xe (bấm lần nữa để mở bảng đổi xe) · 'map' Bản đồ showroom · 'schedule' Lịch.
 *  Nút "Ẩn bảng" thu gọn workspace, nút "Hiện bảng" nổi bên trái để mở lại.
 *
 * ⚠️ ══ ĐIỀU PHẢI BIẾT TRƯỚC KHI SỬA GIAO DIỆN ══
 *  Bên backend đã tách một số phần ra components/booking/, NHƯNG file này vẫn giữ bản sao
 *  cũ của nhiều component. Hai bản tồn tại song song, và bản đang chạy thật là:
 *
 *   ĐANG CHẠY từ components/booking/ — sửa ở file riêng:
 *     · ShowroomMap (import tên BookingShowroomMap) · BookingCustomerForm
 *     · SchedulePanel + BookingTicket (BookingSummary.jsx) · BookingAccessPanel
 *     · CancellationConfirmModal + RescheduleConfirmModal
 *
 *   ĐANG CHẠY từ CHÍNH FILE NÀY — sửa ngay tại đây:
 *     · RecipientModal (~239) · AgentMessage (~264) · ViViAvatar (~287)
 *     · ContextualChoices (~295) · VehicleShot (~347) · VehicleSwitcher (~358) · VehiclePanel (~424)
 *
 *   CODE CHẾT, sửa vào cũng không thấy gì đổi:
 *     · ShowroomMap bản cũ trong file này (~446–634) — đã thay bằng bản import.
 *     · Cả file components/booking/BookingChatPrimitives.jsx — không ai import.
 *     · VehicleSwitcher + VehiclePanel trong components/booking/VehicleWorkspace.jsx.
 *
 * ══ CÁC HÀM CHÍNH (theo thứ tự người dùng bấm) ══
 *  beginConversation(~1056) chọn đặt cho ai · chooseCar(~1077) / switchCar(~1092) chọn & đổi xe
 *  requestUserLocation(~753) lấy GPS · loadShowrooms(~967) tìm showroom · chooseShowroom(~1125)
 *  chooseSlot(~1149) mở popup giờ · confirmSlot(~1154) GIỮ CHỖ và bật đếm ngược
 *  submitPerson(~1401) kiểm tra form · submitBooking(~1428) chốt đặt lịch
 *  Sau response thành công: BookingSuccessCinematic chạy trước, rồi mới set stage success.
 *  handlePrompt(~1186) xử lý khi người dùng gõ tin nhắn tự do cho ViVi
 *  applyAgentToolResult(~812) — hàm khó nhất: dịch kết quả backend trả về thành trạng thái giao diện
 *  Nhánh OTP: requestAccessOtp(~1247) · verifyAccessOtp(~1267) · saveAccessProfile(~1299)
 *             confirmCancellation(~1320) · holdReschedule(~1352) · confirmReschedule(~1363)
 *
 * ══ CÒN DỮ LIỆU GIẢ ══
 *  showroomDirectory (~68): 12 showroom hard-code kèm toạ độ x/y và tên nhân viên sale.
 *  Nay backend đã trả showroom thật; mảng này chỉ còn dùng để đoán tỉnh/thành từ chữ người
 *  dùng gõ. Đừng tin cột `staff` trong đó.
 *
 * ══ SỬA GIAO DIỆN Ở ĐÂU ══
 *  Style: mục "Booking experience" và "Agent-first booking studio" trong index.css.
 *  Riêng nút "Hiện bảng" (~1498) và nút đóng workspace viết inline style ngay trong file.
 *  Trang này KHÔNG dùng AppShell — header riêng, gọn hơn, ở ~dòng 1488.
 */
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  CalendarBlank,
  CarProfile,
  CaretDown,
  CaretLeft,
  Check,
  CheckCircle,
  ChatCircleDots,
  Clock,
  Crosshair,
  List,
  MapPin,
  Minus,
  NavigationArrow,
  PaperPlaneTilt,
  PencilSimple,
  Prohibit,
  Plus,
  ShieldCheck,
  SquaresFour,
  User,
  UserPlus,
  X,
} from '@phosphor-icons/react'
import { Brand } from '../components/Brand'
import { SmartImage } from '../components/SmartImage'
import { carGroups } from '../data/cars'
import { useBookingUpsell, useVehicleCatalog } from '../hooks/useSiteData'
import { BookingUpsell } from '../components/booking/BookingUpsell'
import { viviAvatar } from '../data/media'
import { commonMedia } from '../media/assets'
import {
  confirmHeldBooking,
  cancelVerifiedBooking,
  confirmVerifiedReschedule,
  holdBookingSlot,
  releaseBookingHold,
  holdVerifiedReschedule,
  getVerifiedBooking,
  getDriverInvitationContext,
  getFloatingDemoCapabilities,
  listVerifiedBookings,
  requestBookingAccess,
  resetBookingConversation,
  saveBookingCustomer,
  searchFloatingDemoOptions,
  sendDriverChatMessage,
  sendBookingMessage,
  searchBookingOptions,
  searchBookingCalendar,
  updateVerifiedBooking,
  verifyBookingAccess,
} from '../api/booking'
import {
  BookingMode,
  BookingPhase,
  InteractionEvent,
  bookingInteractionReducer,
  createInteractionState,
  selectAllowedActions,
  selectComposerMode,
  selectWorkspace,
  serializeInteractionState,
  toLegacyStage,
} from '../state/bookingInteraction'
import { CHAT_MESSAGE_MAX_LENGTH } from '../api/contracts'
import { actionId } from '../api/ids'
import { useBackendStatus } from '../context/BackendStatusContext'
import { BookingCustomerForm as CustomerForm } from '../components/booking/BookingCustomerForm'
import { ShowroomMap as BookingShowroomMap } from '../components/booking/ShowroomMap'
import { BookingNextSteps, BookingTicket, SchedulePanel, buildGoogleCalendarUrl } from '../components/booking/BookingSummary'
import { BookingAccessPanel } from '../components/booking/BookingAccessPanel'
import { CancellationConfirmModal, RescheduleConfirmModal } from '../components/booking/BookingManagementModals'
import { BookingSuccessVehicleModel, preloadVehicle3dRuntime } from '../components/Vehicle3DExperience'
import { BookingSuccessCinematic } from '../components/BookingSuccessCinematic'
import { getVehicle3dModel } from '../data/vehicle3d'
import { DemoCompletionModal, RecipientModal, ResumeModal } from '../components/booking/BookingModalPrimitives'
import { AgentMessage, ViviStatusTyping, ViViAvatar, ContextualChoices } from '../components/booking/BookingChatPrimitives'
import { VehicleShot, VehicleSwitcher, VehiclePanel } from '../components/booking/VehicleWorkspace'
import { BookingActionMenu } from '../components/booking/BookingActionMenu'
import { BookingHeader } from '../components/booking/BookingHeader'
import { FloatingDemoBar } from '../components/booking/FloatingDemoBar'
import { useDialogFocus } from '../hooks/useDialogFocus'
import { clearBookingReturnContext, takeBookingReturnContext } from '../utils/bookingReturnContext'
import { calendarRequestForSearch, groupSlots, heldSlotFromResult, mergeAvailability } from '../state/bookingSchedule'

const HOLD_TTL_MS = 5 * 60 * 1000
const FLOATING_DEMO_STEP_DELAY_MS = 3500
const BOOKING_MOBILE_MEDIA_QUERY = '(max-width: 900px)'
const DEMO_PERSONA = Object.freeze({
  bookingName: 'Nguyễn Hải Đăng',
  driverName: '',
  phone: '0912 345 678',
  email: 'haidang.vinfast@demo.vn',
  driverSameContact: true,
  driverPhone: '',
  driverEmail: '',
  hasLicense: true,
  marketingConsent: false,
})
const vinfastLogo = commonMedia.vinfastLogo
const driveCars = []
const BOOKING_UI_STATE_KEY = 'vinfast:booking-ui-state'
const DRIVER_INVITATION_HISTORY_KEY = 'vinfastDriverInvitationToken'
const BOOKING_PREPARATION_GREETING =
  'ViVi sẽ đồng hành cùng Anh/Chị chuẩn bị cho buổi lái thử. Ngoài việc giải đáp về xe, ViVi có thể giúp Anh/Chị xác định những nội dung nên ưu tiên trải nghiệm, các điểm cần trao đổi với tư vấn viên và cách đánh giá xe sát với nhu cầu sử dụng thực tế. Nếu buổi lái thử có người thân hoặc người khác cùng tham gia đánh giá, Anh/Chị cũng có thể chia sẻ để ViVi gợi ý những điểm mỗi người nên chú ý. Càng hiểu rõ cách Anh/Chị dự định sử dụng xe và những ai sẽ cùng trải nghiệm, ViVi càng có thể giúp buổi lái thử tập trung vào những điều thực sự quan trọng.'
const postBookingGreetingFollowUps = (role) => (
  role === 'driver'
    ? [
        { text: 'Tôi muốn xác định những gì mình nên ưu tiên trải nghiệm' },
        { text: 'Tôi muốn biết những điểm đáng chú ý khi lái mẫu xe này' },
      ]
    : [
        { text: 'Tôi muốn chuẩn bị cho buổi lái thử cùng gia đình/người đi cùng' },
        { text: 'Tôi muốn biết những điểm đáng chú ý trên mẫu xe này' },
      ]
)
const VIETNAM_SLOT_DATE_TIME_FORMATTER = new Intl.DateTimeFormat('en-US', {
  timeZone: 'Asia/Ho_Chi_Minh',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

const getVietnamSlotDateTime = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  const values = Object.fromEntries(
    VIETNAM_SLOT_DATE_TIME_FORMATTER.formatToParts(date)
      .filter((part) => part.type !== 'literal')
      .map((part) => [part.type, part.value]),
  )
  if (!values.year || !values.month || !values.day || values.hour === undefined || !values.minute) return null
  return {
    date: `${values.year}-${values.month}-${values.day}`,
    minutes: Number(values.hour) * 60 + Number(values.minute),
  }
}
const driverGreeting = ({ driver, booking }) => {
  const name = driver?.name || 'bạn'
  const vehicle = booking?.vehicle_model || 'xe VinFast'
  const showroom = booking?.showroom_name || 'showroom VinFast'

  return `Chào ${name}, ViVi rất vui được đồng hành cùng bạn trong buổi lái thử ${vehicle} tại ${showroom}. ViVi có thể giúp Anh/Chị xác định những điểm nên ưu tiên trải nghiệm, những nội dung cần trao đổi với tư vấn viên và các tiêu chí đáng chú ý dựa trên cách Anh/Chị dự định sử dụng xe. Nếu có người thân hoặc người khác cùng tham gia đánh giá chiếc xe, Anh/Chị cũng có thể chia sẻ để ViVi giúp chuẩn bị trải nghiệm phù hợp cho cả buổi lái thử.`
}

const extractRescheduleIntent = (text = '', intentEntities = null) => {
  let targetDate = intentEntities?.reschedule_target_date || ''
  let targetTime = intentEntities?.reschedule_target_time || ''
  const codeMatch = (text || '').toUpperCase().match(/\b(VF[A-Z0-9]{6,16})\b/)
  const bookingCode = intentEntities?.booking_code || (codeMatch ? codeMatch[1] : '')
  if (!targetDate || !targetTime) {
    const lower = (text || '').toLowerCase()
    const dateMatch = lower.match(/(?:sang|ngày|ngay|vao|vào)\s+(\d{1,2})(?:[\/\-\.](\d{1,2}))?/)
      || lower.match(/(\d{1,2})[\/\-](\d{1,2})/)
    if (dateMatch && !targetDate) {
      const day = dateMatch[1].padStart(2, '0')
      const month = (dateMatch[2] || '08').padStart(2, '0')
      targetDate = `2026-${month}-${day}`
    }
    const timeMatch = lower.match(/(\d{1,2})(?:h|:| giờ\s*)(\d{1,2})?\s*(sáng|chiều|tối|pm|am)?/)
      || lower.match(/(\d{1,2})\s*giờ\s*(chiều|tối|sáng)?/)
    if (timeMatch && !targetTime) {
      let hours = parseInt(timeMatch[1], 10)
      const minutes = parseInt(timeMatch[2] || '0', 10)
      const period = (timeMatch[3] || timeMatch[2] || '').toLowerCase()
      if ((period.includes('chiều') || period.includes('tối') || period.includes('pm')) && hours < 12) {
        hours += 12
      } else if (hours >= 1 && hours <= 6 && !period.includes('sáng') && !period.includes('am')) {
        hours += 12
      }
      targetTime = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
    }
  }
  return { targetDate, targetTime, bookingCode }
}

const takeDriverInvitationToken = () => {
  const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  const token = params.get('driver-invitation') || ''
  const state = window.history.state && typeof window.history.state === 'object'
    ? window.history.state
    : {}
  if (!token) return typeof state[DRIVER_INVITATION_HISTORY_KEY] === 'string'
    ? state[DRIVER_INVITATION_HISTORY_KEY]
    : ''
  params.delete('driver-invitation')
  const hash = params.toString()
  window.history.replaceState(
    { ...state, [DRIVER_INVITATION_HISTORY_KEY]: token },
    '',
    `${window.location.pathname}${window.location.search}${hash ? `#${hash}` : ''}`,
  )
  return token
}

// Dùng chung cho cả người đặt lẫn người lái — hai đầu mối phải được kiểm cùng một chuẩn.
const PHONE_PATTERN = /^(0|\+84)[0-9\s.-]{8,12}$/
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Đổi lỗi của bước xin OTP thành câu người dùng hiểu và làm được gì đó.
 *
 * Vì sao cần: khi kênh gửi OTP chưa được cấu hình đúng, backend ném 500 và `apiPost`
 * chỉ còn câu mặc định "Yêu cầu không thành công." — người dùng không biết chuyện gì
 * xảy ra, cũng không biết nên làm gì tiếp.
 *
 * TODO [BACKEND/OTP]: 500 nên đổi thành lỗi có mã (vd OTP_CHANNEL_UNAVAILABLE) để
 * frontend phân biệt được "cấu hình sai" với "mạng lỗi".
 */
/**
 * Tạo file .ics cho buổi lái thử và tải xuống.
 *
 * Vì sao có: no-show là vấn đề lõi của dự án (nghiên cứu người dùng: một người tham gia
 * đã bỏ hẹn thật). Cho người dùng đưa buổi hẹn thẳng vào lịch điện thoại là cách chống
 * quên rẻ nhất, và làm được HOÀN TOÀN ở frontend — không phụ thuộc email/OTP đang hỏng.
 *
 * Chỉ ghi dữ liệu có thật: giờ bắt đầu/kết thúc từ slot, tên + địa chỉ showroom, mã lịch.
 * Không có giờ kết thúc thì mặc định 60 phút và ghi rõ trong mô tả là ước tính.
 */
const escapeIcs = (value = '') => String(value)
  .replace(/\\/g, '\\\\')
  .replace(/;/g, '\\;')
  .replace(/,/g, '\\,')
  .replace(/\r?\n/g, '\\n')

const downloadCalendarInvite = ({ car, showroom, slot, bookingCode }) => {
  let start = null
  let end = null

  if (slot?.startAt) {
    start = new Date(slot.startAt)
    end = slot.endAt ? new Date(slot.endAt) : new Date(start.getTime() + 45 * 60000)
  } else if (slot?.date && slot?.time) {
    const timeClean = slot.time.length === 5 ? slot.time : slot.time.padStart(5, '0')
    const dateStr = `${slot.date}T${timeClean}:00+07:00`
    start = new Date(dateStr)
    end = new Date(start.getTime() + 45 * 60000)
  }

  if (!start || isNaN(start.getTime())) return false
  const stamp = (date) => date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')

  const description = [
    `Mã lịch: ${bookingCode || 'Tạm giữ'}`,
    'Mang theo giấy phép lái xe còn hiệu lực.',
    showroom?.phone ? `Showroom: ${showroom.phone}` : '',
    !slot?.endAt ? '(Thời lượng ước tính: 45 phút, showroom sẽ đón tiếp trực tiếp.)' : '',
  ].filter(Boolean).join('\n')

  const ics = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//VinFast//Test Drive//VI',
    'BEGIN:VEVENT',
    `UID:${bookingCode || 'booking'}-${Date.now()}@vinfast`,
    `DTSTAMP:${stamp(new Date())}`,
    `DTSTART:${stamp(start)}`,
    `DTEND:${stamp(end)}`,
    `SUMMARY:${escapeIcs(`Lái thử ${car?.name || 'VinFast'} · ${bookingCode || 'Lịch hẹn'}`)}`,
    `LOCATION:${escapeIcs([showroom?.name, showroom?.address].filter(Boolean).join(', '))}`,
    `DESCRIPTION:${escapeIcs(description)}`,
    'BEGIN:VALARM',
    'TRIGGER:-PT2H',
    'ACTION:DISPLAY',
    'DESCRIPTION:Buổi lái thử VinFast sắp bắt đầu',
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR',
  ].join('\r\n')

  const url = URL.createObjectURL(new Blob([ics], { type: 'text/calendar;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `lai-thu-${bookingCode || 'vinfast'}.ics`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
  return true
}

const accessErrorMessage = (error) => {
  if (error?.code === 'ZALO_NOT_LINKED') {
    return 'Số điện thoại này chưa liên kết với Zalo Bot của VinFast nên bạn chưa nhận được mã.'
  }
  if (error?.code === 'BOOKING_NOT_FOUND' || error?.status === 404) {
    return 'ViVi không tìm thấy lịch nào ứng với thông tin này. Bạn kiểm tra lại email đã dùng khi đặt lịch giúp ViVi nhé.'
  }
  if (error?.status >= 500 || !error?.code) {
    return 'ViVi chưa gửi được mã xác thực cho bạn lúc này. Bạn thử lại sau ít phút, hoặc gọi hotline 1900 23 23 89 để được hỗ trợ trực tiếp.'
  }
  return error.message
}
const normalizeVehicleName = (value = '') => value.toLowerCase().replace(/^vinfast\s+/, '').replace(/[^a-z0-9]/g, '')

const readBookingUiState = () => {
  try {
    const value = window.sessionStorage.getItem(BOOKING_UI_STATE_KEY)
    return value ? JSON.parse(value) : {}
  } catch {
    return {}
  }
}

const isSensitiveChatText = (value) => /(?:\b(?:0|\+84)\d[\d\s.-]{7,}\b|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|\b\d{6}\b)/.test(value)
const formatDistance = (distance) => (
  Number.isFinite(distance) ? `${String(distance).replace('.', ',')} km` : ''
)

// BACKEND HANDOFF: This file is currently a complete frontend prototype/state
// machine with deterministic fixtures. Replace each TODO [BACKEND/*] boundary,
// not the visual components. Canonical contracts and failure behaviour live in
// ../../BACKEND_HANDOFF.md.

// ĐÃ XONG — KHÔNG CÒN CẦN NỐI GÌ Ở ĐÂY.

export function BookingPage() {
  const { bookingStatus, retry } = useBackendStatus()
  // UX state machine (server should return/validate the same nextStage values):
  // idle -> need_car -> need_address -> need_ward -> choose_showroom ->
  // choose_slot -> collect_info -> review -> success. `lookup` is a side flow.
  // The browser may render optimistically, but inventory holds and terminal booking
  // state are always server-authoritative. Full transition table: BACKEND_HANDOFF.md.
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [driverInvitationToken] = useState(takeDriverInvitationToken)
  const isDriverChat = Boolean(driverInvitationToken)
  const { cars } = useVehicleCatalog()
  const [restoredUi] = useState(readBookingUiState)
  const getCar = (id) => cars.find((car) => car.id === id)
  // 3 mẫu upsell do sale admin chọn bên trang quản trị. Không hard-code danh sách xe ở đây
  // nữa: đổi mẫu muốn đẩy là việc của người bán hàng, không phải việc phải sửa code và deploy.
  const upsell = useBookingUpsell()
  const upsellCars = upsell.vehicleIds.map(getCar).filter(Boolean)
  const routeCar = getCar(searchParams.get('car'))
  const initialCar = routeCar || null
  const restoredFloatingDemo = restoredUi.floatingDemo?.enabled && Number(restoredUi.floatingDemo?.step) > 0
    ? restoredUi.floatingDemo
    : null
  const shouldOfferResume = !isDriverChat && Boolean(
    !initialCar && (
      (restoredUi.stage && restoredUi.stage !== 'idle') ||
      (restoredUi.interaction?.phase && restoredUi.interaction.phase !== 'idle') ||
      (Array.isArray(restoredUi.messages) && restoredUi.messages.length) ||
      restoredFloatingDemo
    ),
  )
  const restoredLastConfirmed = useMemo(() => {
    try {
      const storedStr = window.sessionStorage.getItem('LAST_CONFIRMED_BOOKING')
      return storedStr ? JSON.parse(storedStr) : null
    } catch {
      return null
    }
  }, [])

  // LAST_CONFIRMED_BOOKING phục vụ màn hậu booking, không phải nháp cho một chat mới.
  // Chỉ hydrate lại dữ liệu này khi chính UI state đang khôi phục phase success.
  const confirmedUiRestore = shouldOfferResume && (
    restoredUi.interaction?.phase === BookingPhase.SUCCESS || restoredUi.stage === 'success'
  )
    ? restoredLastConfirmed
    : null

  const [recipient, setRecipient] = useState(isDriverChat ? 'driver' : (initialCar ? '' : restoredUi.recipient || ''))
  const [resumePending, setResumePending] = useState(() => Boolean(
    shouldOfferResume,
  ))
  const [selectedCarId, setSelectedCarId] = useState(initialCar?.id || restoredUi.selectedCarId || confirmedUiRestore?.car?.id || '')
  const [interaction, dispatchInteraction] = useReducer(
    bookingInteractionReducer,
    {
      stage: isDriverChat ? 'idle' : (shouldOfferResume ? restoredUi.stage || 'idle' : initialCar ? 'need_address' : 'idle'),
      activeView: isDriverChat ? 'agent' : (initialCar ? 'car' : restoredUi.activeView || 'agent'),
      interaction: shouldOfferResume ? restoredUi.interaction : null,
    },
    createInteractionState,
  )
  const stage = toLegacyStage(interaction)
  const activeView = interaction.activeView
  // Mobile luôn bắt đầu ở ViVi. `activeView` chỉ quyết định nội dung nào được chuẩn bị
  // trong workspace; nó không được tự ý điều hướng người dùng khỏi cuộc hội thoại.
  // Trên desktop hai bề mặt vẫn cùng hiện nên thay đổi này không tác động bố cục cũ.
  const [mobileSurface, setMobileSurface] = useState('assistant')
  const [isMobileBookingViewport, setIsMobileBookingViewport] = useState(() => (
    typeof window !== 'undefined' && window.matchMedia(BOOKING_MOBILE_MEDIA_QUERY).matches
  ))
  useEffect(() => {
    const mediaQuery = window.matchMedia(BOOKING_MOBILE_MEDIA_QUERY)
    const syncViewport = (event) => setIsMobileBookingViewport(event.matches)
    setIsMobileBookingViewport(mediaQuery.matches)
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', syncViewport)
      return () => mediaQuery.removeEventListener('change', syncViewport)
    }
    mediaQuery.addListener(syncViewport)
    return () => mediaQuery.removeListener(syncViewport)
  }, [])
  const setStage = useCallback((nextStage) => {
    dispatchInteraction({ type: InteractionEvent.SET_PHASE, stage: nextStage })
  }, [])
  const setActiveView = useCallback((nextView) => {
    dispatchInteraction({ type: InteractionEvent.SET_ACTIVE_VIEW, activeView: nextView })
  }, [])
  // Hai hàm này chỉ đổi bề mặt đang thấy ở breakpoint mobile. Desktop vẫn render
  // workspace và ViVi song song nên không có thay đổi bố cục hay thứ tự thao tác.
  const showMobileWorkspace = useCallback((nextView) => {
    setActiveView(nextView)
    setMobileSurface('workspace')
  }, [setActiveView])
  const showMobileAssistant = useCallback(() => {
    setMobileSurface('assistant')
  }, [])
  const [messages, setMessages] = useState(isDriverChat
    ? [{ id: 'driver-invitation-greeting', role: 'assistant', text: driverGreeting({}), followUps: postBookingGreetingFollowUps('driver') }]
    : (shouldOfferResume && Array.isArray(restoredUi.messages) ? restoredUi.messages : []))
  // Follow-up chỉ xuất hiện sau khi AgentMessage đã hoàn tất hiệu ứng in chữ.
  // Không dùng `agentTyping` cho việc này vì state đó chỉ biểu thị thời gian chờ API.
  const [completedAssistantMessageId, setCompletedAssistantMessageId] = useState('')
  useEffect(() => {
    if (!driverInvitationToken) return undefined
    let cancelled = false
    getDriverInvitationContext(driverInvitationToken)
      .then((context) => {
        if (!cancelled) {
          setMessages([{ id: 'driver-invitation-greeting', role: 'assistant', text: driverGreeting(context), followUps: postBookingGreetingFollowUps('driver') }])
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [driverInvitationToken])
  const [draft, setDraft] = useState('')
  const [agentTyping, setAgentTyping] = useState(false)
  const [checkingVehicleName, setCheckingVehicleName] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [address, setAddress] = useState(restoredUi.address || { province: '', detail: '' })
  const [locationSuggestions, setLocationSuggestions] = useState([])
  const [nearbyShowrooms, setNearbyShowrooms] = useState(
    Array.isArray(restoredUi.nearbyShowrooms) && restoredUi.nearbyShowrooms.length
      ? restoredUi.nearbyShowrooms
      : confirmedUiRestore?.showroom ? [confirmedUiRestore.showroom] : []
  )
  const [showroomId, setShowroomId] = useState(restoredUi.showroomId || confirmedUiRestore?.showroom?.id || '')
  const [pendingSlot, setPendingSlot] = useState(null)
  const [selectedSlot, setSelectedSlot] = useState(confirmedUiRestore?.slot || null)
  const [confirmSlotOpen, setConfirmSlotOpen] = useState(false)
  const closeSlotDialog = useCallback(() => setConfirmSlotOpen(false), [])
  const slotDialogRef = useDialogFocus({ active: confirmSlotOpen, onClose: closeSlotDialog })
  const [switcherOpen, setSwitcherOpen] = useState(false)
  const [workspaceHidden, setWorkspaceHidden] = useState(false)
  const [person, setPerson] = useState(confirmedUiRestore?.person || {
    bookingName: '',
    driverName: '',
    phone: '',
    email: '',
    driverSameContact: true,
    driverPhone: '',
    driverEmail: '',
    hasLicense: false,
    marketingConsent: true,
  })
  const [formErrors, setFormErrors] = useState({})
  const [bookingCode, setBookingCode] = useState(confirmedUiRestore?.bookingCode || '')
  const [bookingAdvisor, setBookingAdvisor] = useState(confirmedUiRestore?.advisor || null)
  const [submitting, setSubmitting] = useState(false)
  const [successCinematic, setSuccessCinematic] = useState(false)
  const [actionMenuOpen, setActionMenuOpen] = useState(false)
  const [accessFlow, setAccessFlow] = useState(null)
  const [accessValue, setAccessValue] = useState({ bookingCode: '', email: '', otpCode: '' })
  const [accessError, setAccessError] = useState('')
  const [accessBusy, setAccessBusy] = useState(false)
  const [accessSecondsLeft, setAccessSecondsLeft] = useState(0)
  const [resendSecondsLeft, setResendSecondsLeft] = useState(0)
  const [accessProfile, setAccessProfile] = useState(null)
  const [accessibleBookings, setAccessibleBookings] = useState([])
  const [expandedBookingId, setExpandedBookingId] = useState('')
  const [rescheduleState, setRescheduleState] = useState(null)
  const [rescheduleSecondsLeft, setRescheduleSecondsLeft] = useState(0)
  const [slots, setSlots] = useState(Array.isArray(restoredUi.slots) ? restoredUi.slots : [])
  const [calendarState, setCalendarState] = useState({
    loading: false,
    error: restoredUi.calendarIncomplete ? 'Lịch chưa tải đầy đủ.' : '',
  })
  const [serverHighlightedDates, setServerHighlightedDates] = useState([])
  const [bookingId, setBookingId] = useState('')
  const [bookingVersion, setBookingVersion] = useState(0)
  const [holdExpiresAt, setHoldExpiresAt] = useState(null)
  const [timeLeft, setTimeLeft] = useState('')
  const [backendError, setBackendError] = useState('')
  const [userLocation, setUserLocation] = useState(restoredUi.userLocation || null)
  const [searchedLocation, setSearchedLocation] = useState(null)
  const messagesRef = useRef(null)
  const composerRef = useRef(null)
  const lastMessageScrollIntentAtRef = useRef(0)
  const timersRef = useRef([])
  const holdActionIdsRef = useRef(new Map())
  // Đếm lượt tìm khung giờ. Bấm showroom A rồi bấm nhanh sang B sẽ có 2 request cùng bay;
  // ai về sau thắng, nên nếu không đánh số thì slot của A có thể đắp lên tên showroom B.
  const showroomRequestRef = useRef(0)
  // Ngày/giờ khách nói khi chưa chọn showroom. Trước đây bị vứt: chooseShowroom chỉ
  // hỏi lại lịch theo xe + showroom, nên khách nói "VF 9 ngày 4/9 lúc 10:30" rồi bấm
  // showroom là phải dò lại từ đầu. Giữ ở ref chứ không phải state vì nó chỉ dùng đúng
  // một lần ngay sau đó và không được phép gây render lại.
  const pendingScheduleRef = useRef(null)
  const showroomIdRef = useRef(showroomId) // mirror của showroomId để tránh stale closure trong async handlers
  useEffect(() => () => { showroomRequestRef.current += 1 }, [])
  const confirmActionIdsRef = useRef(new Map())
  const holdExpiredRef = useRef(false)
  const otpChallengeIdRef = useRef('')
  const otpCodeRef = useRef('')
  const sendingRef = useRef(false)
  const bookingMutationRef = useRef(false)
  // Sync ref với state để async handlers luôn đọc đúng showroomId mới nhất (tránh stale closure)
  showroomIdRef.current = showroomId
  const driverConversationIdRef = useRef('')

  const [inlineOtpDigits, setInlineOtpDigits] = useState(['', '', '', '', '', ''])
  const [inlineOtpError, setInlineOtpError] = useState('')
  const [inlineOtpBusy, setInlineOtpBusy] = useState(false)
  const [inlineOtpMock, setInlineOtpMock] = useState('')
  const [inlineOtpChallengeId, setInlineOtpChallengeId] = useState('')
  const [demoCompletedModalOpen, setDemoCompletedModalOpen] = useState(false)
  const [floatingDemoEnabled, setFloatingDemoEnabled] = useState(Boolean(restoredFloatingDemo))
  const [floatingDemoStep, setFloatingDemoStep] = useState(() => Number(restoredFloatingDemo?.step) || 0)
  const [floatingDemoRunning, setFloatingDemoRunning] = useState(false)
  const [floatingDemoPaused, setFloatingDemoPaused] = useState(false)
  const [floatingDemoBusy, setFloatingDemoBusy] = useState(false)
  // Desktop demo opens as a complete, shallow controller spanning the two
  // header rows. It never participates in the ViVi header layout.
  const [floatingDemoCollapsed, setFloatingDemoCollapsed] = useState(Boolean(restoredFloatingDemo?.collapsed))
  const [floatingDemoStatus, setFloatingDemoStatus] = useState(restoredFloatingDemo ? 'Đã khôi phục lượt demo trước đó' : '')
  const [floatingDemoLogs, setFloatingDemoLogs] = useState([])
  const floatingDemoRunRef = useRef(0)
  const floatingDemoContextRef = useRef(restoredFloatingDemo?.isSimulated ? { isSimulated: true } : {})
  const floatingDemoPausedRef = useRef(false)
  const floatingDemoPauseWaitersRef = useRef([])
  const floatingDemoDelayWaitersRef = useRef([])
  const floatingDemoMountedRef = useRef(true)
  const pendingRescheduleIntentRef = useRef(null)

  // Auto-play is intentionally cancellable.  Invalidating its run token and
  // resolving pending pauses/delays means an unmounted page never continues a
  // scripted turn or attempts a later state update.
  useEffect(() => {
    floatingDemoMountedRef.current = true
    return () => {
      floatingDemoMountedRef.current = false
      floatingDemoRunRef.current += 1
      floatingDemoPausedRef.current = false
      floatingDemoPauseWaitersRef.current.splice(0).forEach((resolve) => resolve())
      floatingDemoDelayWaitersRef.current.splice(0).forEach((resolve) => resolve())
    }
  }, [])

  const selectedCar = getCar(selectedCarId)
  const leaveRecipientModal = useCallback(() => {
    const returnContext = takeBookingReturnContext()
    if (returnContext) {
      navigate(returnContext.href, {
        replace: true,
        state: { restoreScrollY: returnContext.scrollY },
      })
      return
    }

    // Truy cập thẳng /booking không có trang nguồn: nếu URL mang mã xe thì quay về đúng
    // trang xe đó; còn lại trở về trang chủ thay vì để nút không làm gì.
    const fallbackCarId = routeCar?.id || selectedCar?.id || searchParams.get('car')
    navigate(fallbackCarId ? `/models/${encodeURIComponent(fallbackCarId)}` : '/', { replace: true })
  }, [navigate, routeCar?.id, searchParams, selectedCar?.id])
  const leaveResumeModal = useCallback(() => {
    clearBookingReturnContext()
    navigate('/', { replace: true })
  }, [navigate])
  // ĐÃ XONG: showroom và khung giờ lấy thật từ backend qua searchBookingOptions().
  // Mỗi slot đã mang id thật của backend; cặp ngày/giờ trong UI chỉ để hiển thị.
  const selectedShowroom = nearbyShowrooms.find((showroom) => showroom.id === showroomId)
  // Once a guided run has started, controls stay locked even if the panel is
  // collapsed. Collapsing is presentation-only, not an escape from the flow.
  const floatingDemoMode = floatingDemoEnabled && (floatingDemoRunning || floatingDemoBusy || floatingDemoStep > 0)
  const composerDisabled = isSending || agentTyping || floatingDemoMode
  const allowedActions = useMemo(() => (isDriverChat ? [] : selectAllowedActions(interaction, {
    allowedBookingActions: accessProfile?.allowedActions || [],
  })), [interaction, accessProfile?.allowedActions, isDriverChat])
  const workspaceModel = useMemo(() => selectWorkspace(interaction), [interaction])
  const composerMode = useMemo(() => selectComposerMode(interaction), [interaction])
  const hasWorkspaceContent = Boolean(selectedCar || accessProfile)
  const workspaceVisible = workspaceModel.visible && hasWorkspaceContent && !workspaceHidden

  // Keep a small on-screen trace for demos: it makes a failed API call
  // diagnosable without asking the presenter to open DevTools.
  useEffect(() => {
    if (!floatingDemoStatus) return
    setFloatingDemoLogs((current) => [
      ...current.slice(-7),
      { id: `${Date.now()}-${Math.random()}`, time: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }), text: floatingDemoStatus },
    ])
  }, [floatingDemoStatus])

  /**
   * Kết thúc cinematic → quay về khung chat, KHÔNG chuyển sang trang tĩnh.
   *
   * ViVi chủ động mở lời thay vì để người dùng nhìn một bảng thông tin câm:
   * gọi tên người đặt, nói còn bao nhiêu ngày nữa, và nói rõ mình vẫn ở đây.
   * Số ngày tính từ `slot.startAt` (mốc ISO thật), không đoán từ chuỗi hiển thị.
   */
  // BookingSuccessCinematic đưa `onComplete` vào dependencies của timeline GSAP, nên hàm này
  // PHẢI giữ nguyên identity — đổi một cái là cinematic chạy lại từ đầu. Giữ logic trong ref
  // để vẫn đọc được giá trị mới nhất mà vỏ ngoài không bao giờ đổi.
  const completeSuccessRef = useRef(() => {})
  completeSuccessRef.current = () => {
    setSuccessCinematic(false)
    setStage('success')
    setActiveView('ticket')
    showMobileAssistant()

    // Floating demo still shows the completion guidance, but tags it as step 7
    // so pressing Back removes it together with the confirmation stage.
    if (floatingDemoContextRef.current.isSimulated) {
      const demoName = (person.bookingName || person.driverName || '').trim().split(/\s+/).pop() || ''
      const demoGreeting = demoName ? `${demoName.charAt(0).toUpperCase()}${demoName.slice(1)} ơi, ` : ''
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-${current.length}-demo-success`,
          role: 'assistant',
          text: `${demoGreeting}ViVi đã hoàn tất lượt trình diễn lái thử của bạn.`,
          emphasis: true,
          floatingDemoStep: 7,
        },
        {
          id: `${Date.now()}-${current.length + 1}-demo-next-steps`,
          role: 'assistant',
          type: 'next_steps',
          text: '',
          floatingDemoStep: 7,
        },
        {
          id: `${Date.now()}-${current.length + 2}-demo-preparation`,
          role: 'assistant',
          text: BOOKING_PREPARATION_GREETING,
          followUps: postBookingGreetingFollowUps('booker'),
          floatingDemoStep: 7,
        },
      ])
      setFloatingDemoStatus('Phiếu demo đã hoàn tất')
      window.setTimeout(() => {
        if (floatingDemoMountedRef.current) {
          setDemoCompletedModalOpen(true)
        }
      }, 3000)
      return
    }

    const rawName = (person.bookingName || person.driverName || '').trim().split(/\s+/).pop() || ''
    const firstName = rawName ? rawName.charAt(0).toUpperCase() + rawName.slice(1) : ''
    const greeting = firstName ? `${firstName} ơi, ` : ''

    setMessages((current) => [
      ...current,
      {
        id: `${Date.now()}-${current.length}`,
        role: 'assistant',
        text: `${greeting}ViVi và showroom đều đã nhận được lịch đặt lái thử của bạn.`,
        emphasis: true,
      },
      {
        id: `${Date.now()}-${current.length + 2}-next-steps`,
        role: 'assistant',
        type: 'next_steps',
        text: '',
      },
      {
        id: `${Date.now()}-${current.length + 1}`,
        role: 'assistant',
        text: BOOKING_PREPARATION_GREETING,
        followUps: postBookingGreetingFollowUps('booker'),
      },
    ])
  }
  const completeBookingSuccess = useCallback(() => completeSuccessRef.current(), [])

  useEffect(() => {
    const config = getVehicle3dModel(selectedCarId)
    if (!config) return undefined

    const mobileOrConstrained = window.matchMedia('(max-width: 900px)').matches
      || navigator.connection?.saveData === true
    if (mobileOrConstrained) return undefined

    // Người dùng thường mất vài phút để chọn showroom và điền form. Tận dụng quãng
    // đó để browser cache GLB + runtime, tránh màn chờ ngay sau nút xác nhận cuối.
    preloadVehicle3dRuntime().catch(() => {})
    const link = document.createElement('link')
    link.rel = 'prefetch'
    link.as = 'fetch'
    link.type = 'model/gltf-binary'
    link.href = config.src
    link.crossOrigin = 'anonymous'
    document.head.appendChild(link)
    return () => link.remove()
  }, [selectedCarId])

  useEffect(() => {
    if (isDriverChat) return
    const safeMessages = messages
      .filter((message) => !isSensitiveChatText(message.text || ''))
      .map(({ id, role, text, type, emphasis, floatingDemoStep }) => ({ id, role, text, type, emphasis, floatingDemoStep }))
      .slice(-30)
    window.sessionStorage.setItem(BOOKING_UI_STATE_KEY, JSON.stringify({
      recipient,
      selectedCarId,
      showroomId,
      nearbyShowrooms,
      slots,
      calendarIncomplete: calendarState.loading || Boolean(calendarState.error),
      address,
      userLocation,
      messages: safeMessages,
      interaction: serializeInteractionState(interaction),
      floatingDemo: floatingDemoEnabled && floatingDemoStep > 0
        ? {
            enabled: true,
            step: floatingDemoStep,
            collapsed: floatingDemoCollapsed,
            isSimulated: Boolean(floatingDemoContextRef.current.isSimulated),
          }
        : null,
    }))
  }, [recipient, selectedCarId, showroomId, nearbyShowrooms, slots, calendarState, address, userLocation, messages, interaction, isDriverChat, floatingDemoEnabled, floatingDemoStep, floatingDemoCollapsed])

  useEffect(() => {
    if (selectedCarId || !cars.length) return
    const requestedCar = getCar(searchParams.get('car'))
    if (!requestedCar) return
    setSelectedCarId(requestedCar.id)
    setActiveView('car')
    setWorkspaceHidden(false)
  }, [cars, searchParams, selectedCarId])

  const mapShowrooms = (items, vehicleId = selectedCarId) => items.map((item, index) => ({
    ...item,
    distance: item.distance_km,
    x: 20 + ((index * 23) % 65),
    y: 25 + ((index * 19) % 55),
    models: [vehicleId],
  }))

  const formatBookingSummary = (booking, index = 0) => {
    const startsAt = booking.start_at ? new Date(booking.start_at) : null
    const displayTime = startsAt && !Number.isNaN(startsAt.getTime())
      ? new Intl.DateTimeFormat('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }).format(startsAt)
      : 'Lịch lái thử'
    return {
      ...booking,
      bookingCode: booking.booking_code || booking.bookingCode || '',
      display_time: displayTime,
      display_label: `${index + 1}. ${booking.booking_code || 'Lịch lái thử'} - ${displayTime}${booking.vehicle_name ? ` - ${booking.vehicle_name}` : ''}${booking.showroom_name ? ` tại ${booking.showroom_name}` : ''}`,
    }
  }

  const resolveAgentCar = (vehicle) => {
    if (!vehicle) return null
    const normalize = (value) => String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]/g, '')
    const source = typeof vehicle === 'string' ? { name: vehicle } : vehicle
    const candidates = [
      normalize(source.id),
      normalize(source.code),
      normalize(source.name),
      normalize(source.model),
      normalize(source.vehicle_model),
    ].filter(Boolean)
    return cars.find((car) => candidates.includes(normalize(car.id)) || candidates.includes(normalize(car.name))) || null
  }

  const [isGeolocating, setIsGeolocating] = useState(false)

  const requestUserLocation = ({ addUserMessage = true } = {}) => {
    if (isGeolocating || agentTyping || isSending) return
    if (!navigator.geolocation) {
      setBackendError("Trình duyệt của bạn không hỗ trợ định vị GPS.")
      return
    }
    if (!selectedCar) {
      setStage('need_car')
      setActiveView('car')
      addMessage('assistant', 'Bạn chọn mẫu xe muốn lái thử trước nhé, rồi tôi sẽ xin quyền định vị để tìm showroom gần bạn.')
      return
    }

    setBackendError('')
    setSearchedLocation(null)
    setIsGeolocating(true)
    if (addUserMessage) addMessage('user', 'Định vị vị trí hiện tại của tôi.')
    setAgentTyping(true)

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        setUserLocation({ latitude, longitude })
        
        try {
          const result = await searchBookingOptions({
            vehicleModel: selectedCar.name,
            latitude: latitude,
            longitude: longitude,
          })
          const showrooms = mapShowrooms(result.showrooms || [], selectedCar.id)
          setAddress({ province: '', detail: 'Vị trí hiện tại' })
          setLocationSuggestions([])
          setNearbyShowrooms(showrooms)
          setShowroomId('')
          setAgentTyping(false)
          if (showrooms.length) {
            setStage('choose_showroom')
            showMobileWorkspace('map')
            addMessage('assistant', `ViVi đã định vị vị trí và tìm thấy ${showrooms.length} showroom gần bạn nhất còn lịch cho ${selectedCar.name}. Mời bạn chọn showroom hiển thị trên bản đồ để tiếp tục đặt lịch.`)
          } else {
            setStage('need_address')
            addMessage('assistant', `Rất tiếc, ViVi chưa tìm thấy showroom nào gần vị trí của bạn còn lịch cho ${selectedCar.name}. Bạn hãy thử nhập một địa chỉ cụ thể khác ở khung chat bên dưới nhé.`)
          }
        } catch (error) {
          setAgentTyping(false)
          addMessage('assistant', `Có lỗi xảy ra khi truy vấn dữ liệu showroom: ${error.message}`)
        } finally {
          setIsGeolocating(false)
        }
      },
      (error) => {
        setAgentTyping(false)
        setIsGeolocating(false)
        console.error("Lỗi lấy vị trí: ", error)
        addMessage('assistant', 'ViVi không nhận được phản hồi định vị. Hãy nhắn cho ViVi quận/huyện hoặc tỉnh/thành phố của bạn (ví dụ: "Quận 1, TP HCM") để ViVi tìm showroom nhé!')
      }
    )
  }

  const primeLocationSuggestions = async (car) => {
    try {
      const result = await searchBookingOptions({ vehicleModel: car.name })
      setLocationSuggestions(mapShowrooms(result.showrooms || [], car.id))
    } catch (error) {
      setBackendError(error.message)
      setLocationSuggestions([])
    }
  }

  const completeOtpChallenge = () => {
    setAccessSecondsLeft(0)
    setResendSecondsLeft(0)
    otpChallengeIdRef.current = ''
    otpCodeRef.current = ''
  }

  const clearManagementContext = ({ resetConversation = false, event = InteractionEvent.EXIT_MANAGE_BOOKING } = {}) => {
    setAccessFlow(null)
    setAccessProfile(null)
    setAccessibleBookings([])
    setExpandedBookingId('')
    setRescheduleState(null)
    setRescheduleSecondsLeft(0)
    setAccessError('')
    setAccessSecondsLeft(0)
    setResendSecondsLeft(0)
    setAccessValue({ bookingCode: '', email: '', otpCode: '' })
    otpChallengeIdRef.current = ''
    otpCodeRef.current = ''
    dispatchInteraction({ type: event })
    if (resetConversation) resetBookingConversation()
  }

  const applyServerUiDirective = (ui) => {
    const phaseEvents = {
      access_request: InteractionEvent.ACCESS_REQUESTED,
      access_verify: InteractionEvent.ACCESS_VERIFY,
      booking_list: InteractionEvent.ACCESS_LIST,
    }
    if (phaseEvents[ui?.phase]) {
      dispatchInteraction({ type: phaseEvents[ui.phase] })
      return
    }
    const legacyStages = {
      choose_showroom: 'choose_showroom',
      choose_slot: 'choose_slot',
      collect_info: 'collect_info',
      review: 'review',
      success: 'success',
    }
    if (legacyStages[ui?.phase]) setStage(legacyStages[ui.phase])
  }

  const findSlotById = (groups, slotId) => {
    if (!slotId) return null
    for (const group of groups) {
      const match = group.times.find((item) => item.slotId === slotId)
      if (match) return { date: group.value, dateLabel: group.dateLabel, ...match }
    }
    return null
  }

  // Holds carry authoritative timestamps. Availability searches exclude held
  // slots, so searching again cannot recover a newly held slot.
  const resolveHeldSlot = async (slotId, slotShowroomId, heldData) => {
    const held = heldSlotFromResult(heldData)
    if (held) return held
    const local = findSlotById(slots, slotId)
    if (local) return local
    if (!selectedCar || !slotShowroomId) return null
    try {
      const refreshed = await searchBookingOptions({
        vehicleModel: selectedCar.name,
        showroomId: slotShowroomId,
      })
      const grouped = groupSlots(refreshed.slots || [])
      setSlots(grouped)
      return findSlotById(grouped, slotId)
    } catch {
      return null
    }
  }

  const clearHeldSelection = () => {
    if (bookingId && holdExpiresAt && !bookingCode) {
      releaseBookingHold(bookingId).catch(() => {})
    }
    setPendingSlot(null)
    setSelectedSlot(null)
    setConfirmSlotOpen(false)
    setBookingId('')
    setBookingVersion(0)
    setBookingCode('')
    setBookingAdvisor(null)
    setHoldExpiresAt(null)
    setTimeLeft('')
    setInlineOtpChallengeId('')
    setInlineOtpDigits(['', '', '', '', '', ''])
    setInlineOtpError('')
    setInlineOtpMock('')
    otpChallengeIdRef.current = ''
    holdActionIdsRef.current.clear()
    confirmActionIdsRef.current.clear()
  }

  /**
   * Xoá SẠCH mọi thứ phụ thuộc vào mẫu xe đang chọn.
   *
   * Trước đây ba nhánh đổi xe (chooseCar, switchCar và nhánh `vehicle_info` trong
   * handlePrompt) mỗi nhánh dọn một tập trạng thái khác nhau, và KHÔNG nhánh nào dọn
   * `slots`, `bookingId`, `bookingVersion`, `holdExpiresAt`. Hậu quả đã kiểm chứng:
   * `slots` được ghi vào sessionStorage nên đổi xe rồi tải lại trang là thấy khung giờ
   * của mẫu xe CŨ nằm dưới tên mẫu xe MỚI.
   *
   * Khi đổi xe, luồng chọn slot sẽ gọi API release trước khi giữ slot mới để không
   * khóa oan chỗ của mẫu xe cũ trong thời gian TTL 5 phút.
   */
  const resetSelectionForVehicleChange = () => {
    showroomRequestRef.current += 1 // vô hiệu hoá mọi lượt tìm khung giờ đang bay
    setCalendarState({ loading: false, error: '' })
    clearHeldSelection()
    setNearbyShowrooms([])
    setLocationSuggestions([])
    setShowroomId('')
    setSlots([])
    setAddress({ province: '', detail: '' })
    setServerHighlightedDates([])
    setBackendError('')
  }

  const refreshCalendar = async (request) => {
    const requestId = ++showroomRequestRef.current
    setCalendarState({ loading: true, error: '' })
    try {
      const fullCalendar = await searchBookingCalendar(request)
      if (requestId !== showroomRequestRef.current) return
      if (fullCalendar.search_stage !== 'slot_selection'
        || fullCalendar.selected_showroom?.id !== request.showroomId
        || !Array.isArray(fullCalendar.slots)) {
        throw new Error('Dữ liệu lịch trả về không đúng showroom.')
      }
      // The later full read owns availability. Do not overlay the earlier chat
      // subset, which could reintroduce a slot reserved while this was loading.
      setSlots(groupSlots(fullCalendar.slots))
      setCalendarState({ loading: false, error: '' })
    } catch (error) {
      if (requestId !== showroomRequestRef.current) return
      setCalendarState({ loading: false, error: `Chưa tải được lịch đầy đủ: ${error.message}` })
    }
  }

  const applyAgentToolResult = async (result) => {
    if (!result || !result.action_data) return false
    applyServerUiDirective(result.ui)
    setWorkspaceHidden(false)

    if (result.tool_name === 'request_user_location' || result.action_data.requires_client_geolocation) {
      requestUserLocation({ addUserMessage: false })
      return false
    }

    if (result.tool_name === 'request_booking_access') {
      const data = result.action_data
      const toolInput = result.tool_input || {}
      const accessPurpose = data.purpose || toolInput.purpose || 'manage'
      if (data.requires_contact_value) {
        otpChallengeIdRef.current = ''
        otpCodeRef.current = ''
        dispatchInteraction({ type: InteractionEvent.ACCESS_REQUESTED })
        setAccessError('')
        setAccessSecondsLeft(0)
        setResendSecondsLeft(0)
        const prefilledCode = pendingRescheduleIntentRef.current?.bookingCode || toolInput.booking_code || ''
        setAccessValue((current) => ({
          ...current,
          bookingCode: prefilledCode || current.bookingCode || '',
          email: '',
          otpCode: '',
        }))
        setAccessFlow({ phase: 'request', purpose: accessPurpose, challengeId: '', expiresAt: 0 })
        return false
      }
      const expiresAt = data.expires_at ? new Date(data.expires_at).getTime() : 0
      if (!data.challenge_id || !expiresAt || Number.isNaN(expiresAt)) return
      otpChallengeIdRef.current = data.challenge_id
      otpCodeRef.current = ''
      dispatchInteraction({ type: InteractionEvent.ACCESS_VERIFY })
      setAccessError('')
      setAccessValue((current) => ({
        ...current,
        bookingCode: '',
        email: String(toolInput.contact_value || current.email || ''),
        otpCode: '',
      }))
      setAccessFlow({
        phase: 'verify',
        purpose: accessPurpose,
        challengeId: data.challenge_id,
        expiresAt,
      })
      setAccessSecondsLeft(Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000)))
      setResendSecondsLeft(data.retry_after_seconds || 60)
      return false
    }

    if (result.tool_name === 'verify_booking_access') {
      const verified = result.action_data
      completeOtpChallenge()
      const accessPurpose = accessFlow?.purpose || result.tool_input?.purpose || 'manage'
      const bookings = await listVerifiedBookings({ accessToken: verified.access_session_token })
      const formattedBookings = (bookings.data || bookings || []).map(formatBookingSummary)
      setAccessibleBookings(formattedBookings)
      setActiveView('bookings')
      if (formattedBookings.length > 0) {
        setWorkspaceHidden(false)
        setMobileSurface('workspace')
      }
      const isCancellation = accessPurpose === 'cancel'

      if (formattedBookings.length > 1) {
        setAccessProfile({
          accessToken: verified.access_session_token,
          accessPurpose,
          bookingId: verified.booking_id,
          bookingCode: '',
          bookerName: '',
          driverName: '',
          phone: '',
          email: accessValue.email,
          permissions: verified.permissions || [],
          allowedActions: [],
          vehicleName: '',
          vehicleModelId: '',
          showroomName: '',
          showroomId: '',
          showroomAddress: '',
          advisorName: '',
          advisorPhone: '',
          slotTime: '',
          slotDate: '',
        })
        setExpandedBookingId('')
        setAccessFlow(null)
        dispatchInteraction({ type: InteractionEvent.ACCESS_LIST })
        otpChallengeIdRef.current = ''
        otpCodeRef.current = ''
        addMessage('assistant', `Xác thực thành công. ViVi tìm thấy ${formattedBookings.length} lịch hợp lệ với email này, bạn chọn lịch muốn xem hoặc chỉnh sửa nhé.`)
        return true
      }

      if (formattedBookings.length === 0) {
        clearManagementContext({ resetConversation: false })
        addMessage('assistant', 'Bạn đã xác thực thành công, nhưng ViVi chưa tìm thấy lịch nào còn hiệu lực với email này.')
        return true
      }

      const booking = await getVerifiedBooking({ accessToken: verified.access_session_token, bookingId: formattedBookings[0]?.id || verified.booking_id })
      setAccessProfile({
        accessToken: verified.access_session_token,
        accessPurpose,
        bookingId: booking.id,
        bookingCode: booking.booking_code || '',
        bookerName: booking.booker?.full_name || '',
        driverName: booking.driver?.full_name || '',
        phone: booking.driver?.phone || booking.booker?.phone || '',
        // This form edits the booker. Keep the contact that completed OTP
        // verification instead of pre-filling a different driver's email.
        email: accessValue.email || booking.booker?.email || '',
        permissions: verified.permissions || [],
        allowedActions: booking.allowed_actions || [],
        vehicleName: booking.vehicle?.name || '',
        vehicleModelId: booking.vehicle?.id || '',
        showroomName: booking.showroom?.name || '',
        showroomId: booking.showroom?.id || '',
        showroomAddress: booking.showroom?.address || '',
        advisorName: booking.advisor?.full_name || 'Chưa phân công',
        advisorPhone: booking.advisor?.phone || '',
        slotTime: booking.slot_time || '',
        slotDate: booking.slot_date || '',
      })
      setExpandedBookingId(booking.id)
      setAccessFlow({ phase: isCancellation ? 'confirm_cancel' : 'edit', purpose: accessPurpose, challengeId: '', expiresAt: 0 })
      dispatchInteraction({
        type: isCancellation ? InteractionEvent.ACCESS_CANCEL_CONFIRM : InteractionEvent.ACCESS_EDIT,
      })
      otpChallengeIdRef.current = ''
      otpCodeRef.current = ''
      addMessage('assistant', isCancellation ? 'Xác thực thành công. Vui lòng kiểm tra phiếu bên dưới và xác nhận nếu bạn muốn hủy lịch.' : 'Bạn đã xác thực thành công. Bạn có thể cập nhật thông tin lịch đã đặt ngay bên dưới.')
      return true
    }

    if (result.tool_name === 'search_test_drive_options') {
      // Also supersede a previous calendar refresh for the same selection.
      showroomRequestRef.current += 1
      setCalendarState({ loading: false, error: '' })
      const data = result.action_data
      const toolInput = result.tool_input || {}
      const agentCar = resolveAgentCar(data.resolved_vehicle)
      const vehicleId = agentCar?.id || selectedCarId
      const vehicleChanged = vehicleId !== selectedCarId
      const selectionChanged = vehicleChanged
        || data.search_stage !== 'slot_selection'
        || data.selected_showroom?.id !== showroomIdRef.current
      if (selectionChanged) {
        showroomRequestRef.current += 1
        clearHeldSelection()
        setSlots([])
        setServerHighlightedDates([])
      }

      if (agentCar) {
        if (!recipient) setRecipient('self')
        setWorkspaceHidden(false)
        if (interaction.mode === BookingMode.MANAGE_BOOKING) {
          clearManagementContext({ resetConversation: false, event: InteractionEvent.VIEW_VEHICLE })
        } else {
          dispatchInteraction({ type: InteractionEvent.VIEW_VEHICLE })
        }
        setSelectedCarId(agentCar.id)
      }

      if (data.search_stage === 'showroom_selection') {
        const mapped = mapShowrooms(data.showrooms || [], vehicleId)
        const queriedAddress = String(toolInput.address || '').trim()
        // Khách đã nói giờ nhưng chưa có showroom: nhớ lại để bước sau dùng.
        const requestedDate = String(toolInput.preferred_date || '').slice(0, 10)
        const requestedTime = String(toolInput.preferred_time || '')
        pendingScheduleRef.current = requestedDate || requestedTime
          ? { date: requestedDate, time: requestedTime }
          : null
        setPendingSlot(null)
        setSelectedSlot(null)
        setConfirmSlotOpen(false)
        setShowroomId('')
        setSearchedLocation(data.target_coordinates || null)

        const hasLocationInput = Boolean(queriedAddress || toolInput.latitude || toolInput.longitude || toolInput.showroom_query)
        if (hasLocationInput && mapped.length) {
          if (queriedAddress) setAddress({ province: '', detail: queriedAddress })
          setUserLocation(null)
          setLocationSuggestions([])
          setNearbyShowrooms(mapped)
          setStage('choose_showroom')
          showMobileWorkspace('map')
        } else {
          setAddress({ province: '', detail: queriedAddress })
          setNearbyShowrooms([])
          setLocationSuggestions([])
          setStage('need_address')
          setActiveView('car')
          showMobileAssistant()
        }
        return
      }

      if (data.search_stage === 'location_clarification') {
        const queriedAddress = String(toolInput.address || '').trim()
        setPendingSlot(null)
        setSelectedSlot(null)
        setConfirmSlotOpen(false)
        setShowroomId('')
        setSearchedLocation(null)
        setUserLocation(null)
        setNearbyShowrooms([])
        setLocationSuggestions([])
        setAddress({ province: '', detail: queriedAddress })
        setStage('need_address')
        setActiveView('car')
        showMobileAssistant()
        return
      }

      if (data.search_stage === 'slot_selection' && data.selected_showroom) {
        const [showroom] = mapShowrooms([data.selected_showroom], vehicleId)
        setLocationSuggestions([])
        setNearbyShowrooms((current) => current.some((item) => item.id === showroom.id) ? current : [...current, showroom])
        const newGrouped = groupSlots(data.slots || [])
        const sameSelection = !vehicleChanged && showroom.id === showroomIdRef.current
        setSlots((current) => mergeAvailability(current, newGrouped, { sameSelection, data }))
        setShowroomId(showroom.id)
        if (Array.isArray(data.highlighted_dates) && data.highlighted_dates.length > 0) {
          setServerHighlightedDates(data.highlighted_dates)
        } else if (data.focused_date) {
          setServerHighlightedDates([data.focused_date.slice(5)])
        } else {
          setServerHighlightedDates([])
        }
        setStage('choose_slot')
        showMobileWorkspace('schedule')
        const calendarRequest = calendarRequestForSearch(data, toolInput)
        if (calendarRequest) await refreshCalendar(calendarRequest)
      }
      return
    }

    if (result.tool_name === 'hold_test_drive_slot') {
      const data = result.action_data
      const toolInput = result.tool_input || {}
      // A chat turn can search a different model and hold it before returning.
      // In that case the final hold, not the previous UI vehicle, owns the ticket.
      const heldCar = resolveAgentCar(data.resolved_vehicle)
      if (heldCar && heldCar.id !== selectedCarId) {
        clearHeldSelection()
        setSelectedCarId(heldCar.id)
        setSlots([])
        setServerHighlightedDates([])
      }
      setBookingId(data.booking_id)
      setBookingVersion(data.version ?? 1)
      setHoldExpiresAt(data.hold_expires_at ? new Date(data.hold_expires_at).getTime() : Date.now() + HOLD_TTL_MS)

      let slotShowroomId = showroomId
      if (data.showroom) {
        const [mappedShowroom] = mapShowrooms([data.showroom], heldCar?.id || selectedCarId)
        setNearbyShowrooms((current) => current.some((item) => item.id === mappedShowroom.id) ? current : [...current, mappedShowroom])
        setShowroomId(mappedShowroom.id)
        slotShowroomId = mappedShowroom.id
      }

      const targetSlot = await resolveHeldSlot(toolInput.slot_id, slotShowroomId, data)

      // Không tra được ngày giờ thật thì KHÔNG mở hộp xác nhận. Bắt người dùng bấm
      // "Xác nhận khung giờ" dưới một cái giờ mình tự bịa là điều tệ nhất có thể làm ở đây.
      if (!targetSlot) {
        setPendingSlot(null)
        setSelectedSlot(null)
        setConfirmSlotOpen(false)
        setStage('choose_slot')
        showMobileWorkspace('schedule')
        addMessage('assistant', 'ViVi đã giữ tạm khung giờ này, nhưng chưa đọc lại được chính xác ngày và giờ của nó. Bạn chọn giúp tôi khung giờ trong danh sách bên cạnh để tôi xác nhận đúng thời gian nhé.')
        return true
      }

      setPendingSlot(targetSlot)
      setSelectedSlot(targetSlot)
      setConfirmSlotOpen(true)
      showMobileWorkspace('schedule')
      return
    }

    if (result.tool_name === 'update_booking_draft' || result.tool_name === 'get_booking_draft') {
      const data = result.action_data
      setBookingId(data.id)
      setBookingVersion(data.version ?? 1)
      if (data.hold_expires_at) {
        setHoldExpiresAt(new Date(data.hold_expires_at).getTime())
      }

      const newRecipient = data.recipient_type || 'self'
      setRecipient(newRecipient)

      // Backend trả `full_name`, KHÔNG phải `name` (kiểm chứng 16/08/2026 trên update_draft:
      // booker/driver đều là {id, full_name, phone, email, ...}). Bản cũ đọc `.name` nên nạp
      // lại draft là mất sạch tên người đặt/người lái, và `isComplete` bên dưới luôn sai.
      const draftBookerName = data.booker?.full_name || data.booker?.name || ''
      const draftDriverName = data.driver?.full_name || data.driver?.name || ''
      // Người lái có đầu mối riêng hay không do so sánh dữ liệu backend, không đoán.
      const draftDriverSharesContact = !data.driver
        || (!!data.driver.email && data.driver.email === data.booker?.email
            && (data.driver.phone || '') === (data.booker?.phone || ''))

      // Giữ lại các trường draft KHÔNG mang theo (marketingConsent) bằng cách merge,
      // thay vì thay nguyên object như trước.
      setPerson((current) => ({
        ...current,
        bookingName: draftBookerName,
        driverName: draftDriverName,
        phone: data.booker?.phone || '',
        email: data.booker?.email || '',
        driverSameContact: draftDriverSharesContact,
        driverPhone: draftDriverSharesContact ? '' : (data.driver?.phone || ''),
        driverEmail: draftDriverSharesContact ? '' : (data.driver?.email || ''),
        hasLicense: !!data.license_declaration?.has_driving_license,
      }))

      if (stage === 'choose_slot' || stage === 'choose_showroom' || stage === 'need_address') {
        if (data.showroom) {
          const [mappedShowroom] = mapShowrooms([data.showroom], selectedCarId)
          setNearbyShowrooms((current) => current.some((item) => item.id === mappedShowroom.id) ? current : [...current, mappedShowroom])
          setShowroomId(mappedShowroom.id)
        }

        // Draft CÓ trả slot_date/slot_time thật (lifecycle.py::_draft đọc từ bảng
        // test_drive_slots), nên ưu tiên dữ liệu backend, sau đó mới tới slot đang hiển thị.
        // Không còn chuỗi '21:00 - 22:00' ghi cứng: thiếu giờ thì coi như chưa xác định
        // được slot và quay lại bước chọn giờ.
        const foundSlot = findSlotById(slots, data.slot_id)
        const targetSlot = (data.slot_id && data.slot_time && data.slot_date)
          ? { slotId: data.slot_id, time: data.slot_time, dateLabel: data.slot_date }
          : foundSlot

        if (!targetSlot) {
          setPendingSlot(null)
          setSelectedSlot(null)
          setConfirmSlotOpen(false)
          showMobileWorkspace('schedule')
          setStage('choose_slot')
          addMessage('assistant', 'ViVi chưa đọc lại được chính xác ngày giờ của khung giờ đang giữ. Bạn chọn giúp ViVi một khung giờ trong danh sách bên cạnh nhé.')
          return true
        }

        setPendingSlot(targetSlot)
        setSelectedSlot(targetSlot)
        setConfirmSlotOpen(true)
        showMobileWorkspace('schedule')
        setStage('choose_slot')
        return
      }

      const isComplete = draftBookerName && data.booker?.email && data.license_declaration?.has_driving_license
      if (isComplete) {
        setStage('review')
        setActiveView('ticket')
        showMobileAssistant()
      } else {
        setStage('collect_info')
        setActiveView('schedule')
        showMobileAssistant()
      }
      return
    }

    if (result.tool_name === 'confirm_test_drive_booking') {
      const data = result.action_data
      setBookingCode(data.booking_code)
      setHoldExpiresAt(null)
      setStage('success')
    }
  }

  const loadShowrooms = async (car, detail, province = '') => {
    setBackendError('')
    setAgentTyping(true)
    try {
      const result = await searchBookingOptions({ vehicleModel: car.name, address: detail })
      const showrooms = mapShowrooms(result.showrooms || [], car.id)
      setAddress({ province, detail })
      setUserLocation(null)
      setSearchedLocation(result.target_coordinates || null)
      setLocationSuggestions([])
      setNearbyShowrooms(showrooms)
      setAgentTyping(false)
      if (showrooms.length) {
        setStage('choose_showroom')
        showMobileWorkspace('map')
        reply(`Đã tìm thấy ${showrooms.length} showroom gần “${detail}” còn lịch cho ${car.name}. Hãy chọn một showroom để xem chi tiết khung giờ.`)
      } else {
        setStage('need_address')
        setActiveView('car')
        showMobileAssistant()
        reply(`ViVi chưa tìm thấy showroom còn lịch cho ${car.name} gần “${detail}”. Bạn hãy nhập địa chỉ khác, kèm phường/xã và tỉnh/thành phố.`)
      }
    } catch (error) {
      setAgentTyping(false)
      setStage('need_address')
      setActiveView('car')
      showMobileAssistant()
      reply(`Không tìm được showroom từ địa chỉ này: ${error.message}`)
    }
  }

  useEffect(() => () => timersRef.current.forEach((timer) => window.clearTimeout(timer)), [])

  const markMessageScrollIntent = useCallback(() => {
    lastMessageScrollIntentAtRef.current = Date.now()
  }, [])

  const revealCompletedAssistantMessage = useCallback((messageId) => {
    setCompletedAssistantMessageId(String(messageId))
    if (!window.matchMedia('(max-width: 900px)').matches) return
    if (Date.now() - lastMessageScrollIntentAtRef.current < 3000) return

    window.requestAnimationFrame(() => {
      if (Date.now() - lastMessageScrollIntentAtRef.current < 3000) return
      const container = messagesRef.current
      if (!container) return
      const target = Array.from(container.querySelectorAll('[data-message-id]'))
        .find((element) => element.dataset.messageId === String(messageId))
      if (!target) return

      const containerRect = container.getBoundingClientRect()
      const targetRect = target.getBoundingClientRect()
      const top = Math.max(0, container.scrollTop + targetRect.top - containerRect.top - 12)
      const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      container.scrollTo({ top, behavior: reduceMotion ? 'auto' : 'smooth' })
    })
  }, [])

  useEffect(() => {
    // Tin nhắn, typing indicator và workspace thường đổi trong cùng một lượt render.
    // Chờ layout hoàn tất rồi đặt scrollTop trực tiếp; smooth scrolling có thể bị
    // một render kế tiếp huỷ giữa chừng và khiến tin nhắn mới nằm ngoài khung nhìn.
    const frame = window.requestAnimationFrame(() => {
      const container = messagesRef.current
      const userRecentlyScrolled = window.matchMedia('(max-width: 900px)').matches
        && Date.now() - lastMessageScrollIntentAtRef.current < 3000
      if (container && !userRecentlyScrolled) container.scrollTop = container.scrollHeight
    })
    return () => window.cancelAnimationFrame(frame)
  }, [messages, agentTyping])

  useEffect(() => {
    // Ở mobile, các thẻ chọn xe / showroom nằm phía trên ô nhập trong một vùng cuộn
    // riêng. Mỗi khi bước đặt lịch đổi hoặc người dùng quay lại tab ViVi, đưa vùng đó
    // về cuối để ô nhập hiện ngay — không focus cưỡng bức vì sẽ tự bật bàn phím ảo.
    if (mobileSurface !== 'assistant' || !window.matchMedia('(max-width: 900px)').matches) return undefined
    const frame = window.requestAnimationFrame(() => {
      const composer = composerRef.current
      if (composer) composer.scrollTop = composer.scrollHeight
    })
    return () => window.cancelAnimationFrame(frame)
  }, [mobileSurface, stage, composerMode, selectedCarId, nearbyShowrooms.length, slots.length, upsellCars.length, accessFlow?.phase])

  useEffect(() => {
    if (!holdExpiresAt || successCinematic || (stage !== 'collect_info' && stage !== 'review')) {
      setTimeLeft('')
      return
    }

    const updateTimer = () => {
      // The server decides whether an in-flight save/confirmation beat expiry.
      // Never erase the ticket while its final response is still pending.
      if (bookingMutationRef.current) return
      const diff = holdExpiresAt - Date.now()
      if (diff <= 0) {
        setTimeLeft('Đã hết hạn giữ')
        if (!holdExpiredRef.current) {
          holdExpiredRef.current = true
          const expiredBookingId = bookingId
          const expiredSlotId = selectedSlot?.slotId
          if (expiredBookingId) {
            releaseBookingHold(expiredBookingId).catch(() => {
              // Backend cũng tự thu hồi hold hết hạn khi cleanup hoặc khi slot được giữ lại.
            })
          }
          if (expiredSlotId) {
            setSlots((current) => current.map((day) => ({
              ...day,
              times: day.times.map((slot) => (
                slot.slotId === expiredSlotId
                  ? { ...slot, isAvailable: true, unavailableLabel: '' }
                  : slot
              )),
            })))
          }
          setConfirmSlotOpen(false)
          setPendingSlot(null)
          setSelectedSlot(null)
          setBookingId('')
          setBookingVersion(0)
          setSubmitting(false)
          setInlineOtpDigits(['', '', '', '', '', ''])
          setInlineOtpError('')
          setInlineOtpChallengeId('')
          setInlineOtpMock('')
          setInlineOtpBusy(false)
          setStage('choose_slot')
          showMobileWorkspace('schedule')
          addMessage('assistant', 'Khung giờ ViVi giữ tạm cho bạn đã hết hạn. Bạn chọn lại một khung giờ khác để tôi tiếp tục đặt lịch nhé.')
        }
        return
      }
      const min = Math.floor(diff / 60000)
      const sec = Math.floor((diff % 60000) / 1000)
      setTimeLeft(`${min.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`)
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [bookingId, holdExpiresAt, selectedSlot?.slotId, stage, successCinematic])

  useEffect(() => {
    holdExpiredRef.current = false
  }, [holdExpiresAt])

  const addMessage = (role, text, extra = {}) => {
    // TODO [BACKEND/AGENT]: Use server message ids and timestamps. Store structured
    // cards/actions separately from display text so UI choices stay deterministic.
    setMessages((current) => [...current, { id: `${Date.now()}-${current.length}`, role, text, ...extra }])
  }

  const reply = (text, delay = 420) => {
    // TODO [BACKEND/AGENT]: Replace this cosmetic delay with streamed message state
    // from a future streaming form of POST /api/v1/chat (SSE or fetch stream). Cancel the
    // previous request on stage/vehicle changes and expose retry on failure.
    setAgentTyping(true)
    const timer = window.setTimeout(() => {
      setAgentTyping(false)
      addMessage('assistant', text)
    }, delay)
    timersRef.current.push(timer)
  }

  const beginConversation = (choice) => {
    // TODO [BACKEND/SESSION]: Create/resume an anonymous booking draft here and
    // persist recipientType + selectedVehicleId. Return draftId and expiresAt.
    dismissFloatingDemoForRealFlow()
    clearBookingReturnContext()
    setRecipient(choice)
    const car = selectedCar
    addMessage(
      'assistant',
      'Xin chào, ViVi là trợ lý đặt lịch lái thử VinFast. ViVi có thể tạo lịch mới hoặc hỗ trợ tra cứu, bổ sung và huỷ lịch đã đặt.',
    )
    if (car) {
      setStage('need_address')
      setActiveView('car')
      primeLocationSuggestions(car)
      reply(`Bạn đang xem ${car.name}. Hãy nhập địa chỉ theo phường/xã và tỉnh/thành phố để ViVi tìm showroom có xe lái thử gần bạn.`, 520)
    } else {
      setStage('need_car')
      setActiveView('agent')
      reply('Trước tiên, bạn muốn lái thử mẫu xe nào? Bạn có thể chọn một mẫu ngay phía trên ô nhập hoặc nhắn tên xe cho ViVi.', 520)
    }
  }

  const chooseCar = (car, fromPrompt = false) => {
    if (bookingMutationRef.current || sendingRef.current) return
    if (interaction.mode === BookingMode.MANAGE_BOOKING) {
      clearManagementContext({ event: InteractionEvent.VIEW_VEHICLE })
    }
    setSelectedCarId(car.id)
    setMobileSurface('assistant')
    setWorkspaceHidden(false)
    if (!fromPrompt) addMessage('user', `Tôi muốn lái thử ${car.name}.`)
    resetSelectionForVehicleChange()
    setStage('need_address')
    setActiveView('car')
    primeLocationSuggestions(car)
    reply(`Đã chọn ${car.name}. Bây giờ bạn hãy nhập địa chỉ theo phường/xã và tỉnh/thành phố để tôi tìm showroom gần nhất.`)
  }

  // Đổi mẫu xe sẽ quay lại bước địa chỉ để Agent kiểm tra tồn xe/showroom lại từ đầu.
  const switchCar = (car) => {
    if (bookingMutationRef.current || sendingRef.current) return
    setSwitcherOpen(false)
    if (!car || car.id === selectedCarId) return

    if (interaction.mode === BookingMode.MANAGE_BOOKING) {
      clearManagementContext({ event: InteractionEvent.VIEW_VEHICLE })
    }

    setSelectedCarId(car.id)
    setMobileSurface('assistant')
    addMessage('user', `Tôi muốn đổi sang ${car.name}.`)
    resetSelectionForVehicleChange()
    setStage('need_address')
    setActiveView('car')
    primeLocationSuggestions(car)
    reply(`Đã đổi sang ${car.name}. Bạn cho tôi lại địa chỉ theo phường hoặc xã và tỉnh/thành phố để tìm showroom có sẵn mẫu này.`)
  }

  // Bảng chọn xe dùng chung cho lần chọn đầu tiên và cho việc đổi xe giữa chừng.
  const pickCarFromSwitcher = (car) => {
    setSwitcherOpen(false)
    if (!selectedCarId) chooseCar(car)
    else switchCar(car)
  }

  const resolveSuggestedArea = (showroom) => {
    addMessage('user', `Tìm quanh ${showroom.address}.`)
    loadShowrooms(selectedCar, showroom.address, showroom.province)
  }

  const chooseShowroom = async (showroom, fromPrompt = false) => {
    if (bookingMutationRef.current || sendingRef.current) return
    // ĐÃ XONG một phần: khung giờ đã là dữ liệu thật theo showroom + mẫu xe.
    // TODO [BACKEND/DRAFT — P0]: chưa lưu showroomId lên draft phía server nên đổi máy
    // là mất tiến trình. Chi tiết ở mục 1.3 trong BACKEND_HANDOFF.md.
    if (!fromPrompt) addMessage('user', `Tôi chọn ${showroom.name}.`)
    const requestId = showroomRequestRef.current + 1
    showroomRequestRef.current = requestId
    setCalendarState({ loading: false, error: '' })
    clearHeldSelection()

    setWorkspaceHidden(false)
    setShowroomId(showroom.id)
    setMobileSurface('workspace')
    // Dọn khung giờ của showroom TRƯỚC khi hỏi showroom mới. Nếu để nguyên, trong lúc chờ
    // mạng người dùng vẫn thấy danh sách giờ của showroom cũ trong khi tên showroom đã đổi
    // — bấm vào là giữ chỗ ở showroom này nhưng phiếu ghi showroom kia.
    setSlots([])
    setPendingSlot(null)
    setSelectedSlot(null)
    setBackendError('')
    setAgentTyping(true)
    try {
      const result = await searchBookingOptions({ vehicleModel: selectedCar.name, showroomId: showroom.id })
      if (showroomRequestRef.current !== requestId) return // đã có lượt chọn mới hơn
      const grouped = groupSlots(result.slots || [])
      setSlots(grouped)
      setStage('choose_slot')
      showMobileWorkspace('schedule')
      setAgentTyping(false)

      // Khách đã nói ngày/giờ từ trước thì đưa họ thẳng tới đúng khung giờ đó.
      // Vẫn giữ NGUYÊN lịch đầy đủ của showroom — chỉ tô sáng và mở hộp xác nhận,
      // không lọc bớt, để khách còn thấy lựa chọn khác nếu đổi ý.
      const requested = pendingScheduleRef.current
      pendingScheduleRef.current = null
      const requestedDay = requested?.date ? grouped.find((day) => day.value === requested.date) : null
      const requestedSlot = requested?.time
        ? requestedDay?.times.find((slot) => slot.time === requested.time && slot.isAvailable)
        : null

      // Dạng MM-DD, đúng hợp đồng backend trả ở `highlighted_dates`. BookingSummary
      // parse [month, day] từ chuỗi này (dòng 131) nên đưa YYYY-MM-DD vào là nó đọc
      // 2026 thành tháng và nhảy sai tuần.
      if (requestedDay) setServerHighlightedDates([requestedDay.value.slice(5)])

      if (requestedSlot) {
        // Modal xác nhận đọc `date` và `dateLabel`, mà groupSlots đặt hai trường đó ở
        // cấp NGÀY chứ không ở từng khung giờ. Đưa thẳng entry vào là dòng "Thời gian"
        // hiện "10:30 ·" cụt mất ngày. Ghép cho khớp đúng hình dạng SchedulePanel gửi.
        setPendingSlot({
          date: requestedDay.value,
          dateLabel: requestedDay.dateLabel,
          time: requestedSlot.time,
          slotId: requestedSlot.slotId,
        })
        setConfirmSlotOpen(true)
        reply(`${showroom.name} đã được chọn. Khung giờ ${requestedSlot.time} ${requestedDay.dateLabel} bạn muốn vẫn còn trống, bạn xác nhận giúp ViVi nhé.`)
      } else if (requested?.time && requestedDay) {
        reply(`${showroom.name} đã được chọn. Khung giờ ${requested.time} ${requestedDay.dateLabel} không còn trống, ViVi đã mở lịch ngày đó để bạn chọn giờ khác.`)
      } else if (requested?.date) {
        reply(`${showroom.name} đã được chọn. Ngày bạn muốn chưa có khung giờ trống, ViVi hiện toàn bộ lịch của showroom để bạn chọn.`)
      } else {
        reply(`${showroom.name} đã được chọn. ViVi đã tìm thấy ${result.slots?.length || 0} khung giờ trống cho bạn.`)
      }
    } catch (error) {
      if (showroomRequestRef.current !== requestId) return
      setAgentTyping(false)
      // Lỗi thì trả về đúng bước chọn showroom với trạng thái sạch: không showroom nào
      // đang được chọn, không khung giờ nào đang hiển thị.
      setShowroomId('')
      setSlots([])
      setStage('choose_showroom')
      showMobileWorkspace('map')
      reply(`Không tải được lịch trống của ${showroom.name}: ${error.message}. Bạn chọn lại showroom giúp tôi nhé.`)
    }
  }

  const chooseSlot = (slot) => {
    if (agentTyping || calendarState.loading || sendingRef.current || bookingMutationRef.current) return
    setPendingSlot(slot)
    setConfirmSlotOpen(true)
  }

  const confirmSlot = async () => {
    if (!pendingSlot?.slotId || bookingMutationRef.current || sendingRef.current) return
    bookingMutationRef.current = true
    setSubmitting(true)
    setBackendError('')
    setAgentTyping(true)
    try {
      if (bookingId && selectedSlot?.slotId === pendingSlot.slotId && holdExpiresAt > Date.now()) {
        setConfirmSlotOpen(false)
        setStage('collect_info')
        showMobileAssistant()
        setAgentTyping(false)
        return
      }
      // Nếu đang giữ slot cũ khác → release trước, sau đó mới hold slot mới
      if (bookingId && (!selectedSlot || selectedSlot.slotId !== pendingSlot.slotId)) {
        const oldBookingId = bookingId
        const oldSlotId = selectedSlot?.slotId
        setBookingId('')
        try {
          await releaseBookingHold(oldBookingId)
        } catch {
          // ignore, tiếp tục hold slot mới
        }
        // Khôi phục màu xanh cho slot cũ trên UI
        if (oldSlotId) {
          setSlots((prev) => prev.map((day) => ({
            ...day,
            times: day.times.map((t) =>
              t.slotId === oldSlotId ? { ...t, isAvailable: true, unavailableLabel: '' } : t
            ),
          })))
        }
        holdActionIdsRef.current.clear()
      }
      const actionKey = pendingSlot.slotId
      const uiActionId = holdActionIdsRef.current.get(actionKey) || actionId('hold')
      holdActionIdsRef.current.set(actionKey, uiActionId)
      const held = await holdBookingSlot(pendingSlot.slotId, uiActionId)
      holdActionIdsRef.current.delete(actionKey)
      setBookingId(held.booking_id)
      setBookingVersion(held.version ?? 1)
      setHoldExpiresAt(held.hold_expires_at ? new Date(held.hold_expires_at).getTime() : Date.now() + HOLD_TTL_MS)
      const confirmedSlot = heldSlotFromResult(held) || pendingSlot
      setSelectedSlot(confirmedSlot)
      setPendingSlot(confirmedSlot)
      setConfirmSlotOpen(false)
      addMessage('user', `Tôi xác nhận ${pendingSlot.time}, ${pendingSlot.dateLabel}.`)
      setStage('collect_info')
      showMobileAssistant()
      setAgentTyping(false)
      reply('ViVi đã giữ tạm khung giờ này cho bạn trong 5 phút. Bạn vui lòng điền thông tin để tiếp tục nhé.')
    } catch (error) {
      setAgentTyping(false)
      setConfirmSlotOpen(false)
      if (error.code === 'SLOT_NO_LONGER_AVAILABLE') {
        setPendingSlot(null)
        setSelectedSlot(null)
      }
      reply(`Không thể giữ khung giờ: ${error.message}`)
    } finally {
      bookingMutationRef.current = false
      setSubmitting(false)
      setAgentTyping(false)
    }
  }

  const handlePrompt = async (event, suggestedText = '') => {
    event.preventDefault()
    if (sendingRef.current || bookingMutationRef.current || agentTyping || calendarState.loading) return
    const value = (suggestedText || draft).trim()
    if (!value) return
    if (value.length > CHAT_MESSAGE_MAX_LENGTH) {
      setBackendError(`Tin nhắn không được vượt quá ${CHAT_MESSAGE_MAX_LENGTH.toLocaleString('vi-VN')} ký tự.`)
      return
    }
    sendingRef.current = true
    setIsSending(true)
    setDraft('')
    addMessage('user', value)
    // Highlight server của lượt tìm trước không được che kết quả của câu chat
    // mới; sau khi ViVi trả lời, `highlightedDates` sẽ lấy lại từ response.
    if (stage === 'choose_slot') setServerHighlightedDates([])
    setBackendError('')

    const mentionedCar = isDriverChat ? null : resolveAgentCar(value)
    // Keep the current vehicle and its slots consistent until the search succeeds.
    // A failed chat must not leave VF 9 availability under a VF 3 heading.
    setCheckingVehicleName(mentionedCar?.name || '')

    setAgentTyping(true)
    try {
      const result = isDriverChat
        ? await sendDriverChatMessage(value, {
          conversationId: driverConversationIdRef.current,
          invitationToken: driverInvitationToken,
        })
        : await sendBookingMessage(value, {
        mode: interaction.mode,
        phase: interaction.phase,
        stage,
        allowedActions,
        recipient,
        selectedVehicle: selectedCar ? { id: selectedCar.id, name: selectedCar.name } : null,
        selectedShowroom: selectedShowroom ? { id: selectedShowroom.id, name: selectedShowroom.name } : null,
        selectedSlot,
        nearbyShowrooms: nearbyShowrooms.map((showroom) => ({
          id: showroom.id,
          name: showroom.name,
          address: showroom.address,
          distance: showroom.distance,
        })),
        userLocation,
        bookingId: bookingId || null,
        pendingReschedule: pendingRescheduleIntentRef.current,
        channel: 'booking',
        })
      if (isDriverChat) {
        driverConversationIdRef.current = result.conversation_id || driverConversationIdRef.current
        addMessage('assistant', result.response, { followUps: result.follow_ups || [] })
        return
      }
      const extractedReschedule = extractRescheduleIntent(value, result.intent_entities)
      if (result.intent === 'booking_reschedule' || extractedReschedule.targetDate || extractedReschedule.targetTime || extractedReschedule.bookingCode || /đổi\s*lịch|dời\s*lịch|chuyển\s*lịch/i.test(value)) {
        const previousIntent = pendingRescheduleIntentRef.current || {}
        pendingRescheduleIntentRef.current = {
          reschedule_date_type: result.intent_entities?.reschedule_date_type ?? previousIntent.reschedule_date_type ?? '',
          reschedule_day_offset: result.intent_entities?.reschedule_day_offset ?? previousIntent.reschedule_day_offset ?? null,
          reschedule_target_date: extractedReschedule.targetDate || result.intent_entities?.reschedule_target_date || previousIntent.reschedule_target_date || '',
          reschedule_target_time: extractedReschedule.targetTime || result.intent_entities?.reschedule_target_time || previousIntent.reschedule_target_time || '',
          bookingCode: extractedReschedule.bookingCode || result.intent_entities?.booking_code || previousIntent.bookingCode || '',
        }
      }
      if (mentionedCar && (result.sub_intent || result.intent) === 'vehicle_info' && !result.action_error) {
        if (interaction.mode === BookingMode.MANAGE_BOOKING) {
          clearManagementContext({ event: InteractionEvent.VIEW_VEHICLE })
        }
        setSelectedCarId(mentionedCar.id)
        resetSelectionForVehicleChange()
        setStage('need_address')
        setActiveView('car')
        primeLocationSuggestions(mentionedCar)
      }
      const handledMessage = await applyAgentToolResult(result)
      if (!handledMessage) addMessage('assistant', result.response, { followUps: result.follow_ups || [] })
    } catch (error) {
      addMessage('assistant', `Không thể kết nối ViVi: ${error.message}`)
    } finally {
      setAgentTyping(false)
      setCheckingVehicleName('')
      sendingRef.current = false
      setIsSending(false)
    }
  }

  const startLookup = ({ addUserMessage = true, email = '' } = {}) => {
    // ĐÃ XONG: tra cứu chạy thật qua requestBookingAccess + verifyBookingAccess
    // (OTP gửi bằng email). Chỉ sau khi xác thực mới mở được sửa/huỷ/đổi lịch.
    // TODO [BACKEND/ENDPOINT — P0]: các action này vẫn đi qua /api/v1/demo/action;
    // cần endpoint mang tên thật cho nghiệp vụ production.
    dismissFloatingDemoForRealFlow()
    if (addUserMessage) addMessage('user', 'Tôi muốn tra cứu lịch đã đặt.')
    dispatchInteraction({ type: InteractionEvent.START_LOOKUP })
    setWorkspaceHidden(false)
    setAccessError('')
    otpChallengeIdRef.current = ''
    // A lookup/edit session also needs reschedule permission for the calendar
    // icon. The backend grants update_details as part of this purpose.
    setAccessValue((current) => ({ ...current, bookingCode: '', email: email || current.email, otpCode: '' }))
    // Xin purpose 'manage': một lần OTP là có đủ quyền xem, đổi giờ VÀ huỷ lịch.
    // Trước đây xin 'reschedule' nên phiên không bao giờ có 'cancel_booking', khiến nút
    // "Huỷ lịch" trong danh sách không bao giờ hiện (nút gate theo allowed_actions của backend).
    setAccessFlow({ phase: 'request', purpose: 'manage', challengeId: '', expiresAt: 0 })
    reply('Để bảo vệ lịch của bạn, hãy nhập email đã đăng ký. ViVi sẽ gửi OTP qua email.')
  }

  /**
   * Deep-link `/booking?lookup=1` — mở thẳng luồng tra cứu lịch đã đặt.
   *
   * Trang chủ cần một lối vào cho khách QUAY LẠI (xem/đổi/huỷ lịch), nhưng trước đây
   * `/booking` chỉ nhận `?car=` nên không có cách nào trỏ thẳng vào bước tra cứu —
   * người dùng buộc phải vào luồng đặt mới rồi tự tìm đường sang.
   *
   * Bỏ qua luôn hộp "Bạn đặt lịch cho ai": câu đó chỉ có nghĩa với người đang đặt MỚI.
   */
  const lookupRequested = searchParams.get('lookup')
  useEffect(() => {
    if (!lookupRequested) return
    if (interaction.mode === BookingMode.MANAGE_BOOKING) return
    setRecipient((current) => current || 'self')
    setResumePending(false)
    startLookup({ addUserMessage: false })
    // Chỉ chạy khi URL đổi; startLookup được dựng lại mỗi lần render nên không đưa vào deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lookupRequested])

  const addBookingToCalendar = () => {
    addMessage('user', 'Thêm buổi lái thử vào lịch của tôi.')

    let carToUse = selectedCar
    let showroomToUse = selectedShowroom
    let slotToUse = selectedSlot
    let codeToUse = bookingCode
    let advisorToUse = bookingAdvisor

    if (!slotToUse || !carToUse || !showroomToUse) {
      try {
        const storedStr = window.sessionStorage.getItem('LAST_CONFIRMED_BOOKING')
        if (storedStr) {
          const stored = JSON.parse(storedStr)
          carToUse = carToUse || stored.car
          showroomToUse = showroomToUse || stored.showroom
          slotToUse = slotToUse || stored.slot
          codeToUse = codeToUse || stored.bookingCode
          advisorToUse = advisorToUse || stored.advisor
        }
      } catch (e) {
        console.error('Lỗi đọc LAST_CONFIRMED_BOOKING:', e)
      }
    }

    const gcalUrl = buildGoogleCalendarUrl({
      car: carToUse,
      showroom: showroomToUse,
      slot: slotToUse,
      bookingCode: codeToUse,
      advisor: advisorToUse,
    })

    if (gcalUrl) {
      window.open(gcalUrl, '_blank', 'noopener,noreferrer')
      reply('ViVi đã mở sẵn trang Google Calendar với đầy đủ thông tin buổi lái thử cho bạn. Bạn chỉ cần bấm "Lưu" để hoàn tất nhé!')
    } else {
      reply('ViVi chưa đọc được chính xác mốc thời gian của buổi hẹn nên chưa mở được Google Calendar. Bạn xem giờ hẹn trên phiếu bên cạnh giúp ViVi nhé.')
    }
  }

  const bookAnotherVehicle = () => {
    addMessage('user', 'Tôi muốn đặt thêm lịch cho một mẫu xe khác.')
    window.sessionStorage.removeItem('LAST_CONFIRMED_BOOKING')
    setBookingCode('')
    setBookingAdvisor(null)
    setSelectedCarId('')
    resetSelectionForVehicleChange()
    setStage('need_car')
    setActiveView('agent')
    setSwitcherOpen(true)
    reply('Được ngay. Lịch vừa đặt vẫn được giữ nguyên, bạn tra cứu lại bất cứ lúc nào bằng email đã đăng ký. Bây giờ bạn muốn lái thử mẫu nào?')
  }

  const changeAccessValue = (field, value) => {
    if (field === 'otpCode') otpCodeRef.current = value
    setAccessValue((current) => ({ ...current, [field]: value }))
  }

  const requestAccessOtp = async (event) => {
    event?.preventDefault()
    setAccessBusy(true); setAccessError('')
    try {
      const result = await requestBookingAccess({ bookingCode: accessValue.bookingCode.trim(), email: accessValue.email.trim(), purpose: accessFlow?.purpose || 'manage' })
      if (!result?.challenge_id || !result?.expires_at) {
        throw new Error('ViVi chưa mở được phiên xác thực OTP cho bạn. Bạn bấm gửi lại mã giúp ViVi nhé.')
      }
      const expiresAt = new Date(result.expires_at).getTime()
      if (Number.isNaN(expiresAt)) {
        throw new Error('ViVi đọc không được thời hạn của mã OTP này. Bạn bấm gửi lại mã giúp ViVi nhé.')
      }
      otpChallengeIdRef.current = result.challenge_id
      setAccessFlow((current) => ({ phase: 'verify', purpose: current?.purpose || 'update_details', challengeId: result.challenge_id, expiresAt }))
      dispatchInteraction({ type: InteractionEvent.ACCESS_VERIFY })
      otpCodeRef.current = ''
      setAccessValue((current) => ({ ...current, otpCode: '' }))
      setAccessSecondsLeft(Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000)))
      setResendSecondsLeft(result.retry_after_seconds || 60)
      const mockOtp = result.is_mock ? result.otp_code : ''
      addMessage(
        'assistant',
        mockOtp
          ? `Mã OTP mock của bạn là **${mockOtp}**. Nhập mã này để tiếp tục luồng kiểm thử.`
          : 'ViVi đã gửi mã OTP qua email. Bạn vui lòng nhập mã để tiếp tục.',
      )
    } catch (error) {
      // Hai mã giới hạn KHÁC nhau và trước đây chỉ bắt một: OTP_RATE_LIMITED là cooldown
      // ngắn giữa 2 lần gửi, RATE_LIMIT_EXCEEDED là khoá dài theo giờ. Không khoá nút ở
      // trường hợp thứ hai thì người dùng bấm tiếp và mỗi lần bấm lại gia hạn thêm khoá.
      if (error.code === 'OTP_RATE_LIMITED' || error.code === 'RATE_LIMIT_EXCEEDED') {
        const seconds = Number(error.message.match(/\d+/)?.[0] || 0)
        if (seconds > 0) setResendSecondsLeft(seconds)
      }

      const message = accessErrorMessage(error)
      // Hiện NGAY CẠNH form (role="alert") chứ không chỉ thả vào khung chat: form báo lỗi
      // ở đâu thì người dùng tìm ở đó. Bản cũ còn setAccessError('') làm form sạch trơn.
      setAccessError(message)
      addMessage('assistant', message)
    } finally { setAccessBusy(false) }
  }

  const verifyAccessOtp = async (otpOverride = '') => {
    const challengeId = otpChallengeIdRef.current || accessFlow?.challengeId
    if (!challengeId) {
      setAccessError('')
      addMessage('assistant', 'Phiên xác thực của bạn chưa sẵn sàng hoặc đã hết hạn. Bạn bấm gửi lại mã để tôi cấp mã mới nhé.')
      return
    }
    setAccessBusy(true); setAccessError('')
    try {
      const otpCode = typeof otpOverride === 'string' && otpOverride ? otpOverride : otpCodeRef.current
      const verified = await verifyBookingAccess({ challengeId, otpCode })
      completeOtpChallenge()
      const bookings = await listVerifiedBookings({ accessToken: verified.access_session_token })
      const formattedBookings = (bookings.data || bookings || []).map(formatBookingSummary)
      setAccessibleBookings(formattedBookings)
      setWorkspaceHidden(false)
      setActiveView('bookings')
      if (formattedBookings.length > 0) setMobileSurface('workspace')
      const accessPurpose = accessFlow?.purpose || 'manage'
      const isCancellation = accessPurpose === 'cancel'

      if (accessPurpose === 'confirm_booking') {
        const actionKey = `${bookingId}:${bookingVersion}`
        const uiActionId = confirmActionIdsRef.current.get(actionKey) || actionId('confirm')
        confirmActionIdsRef.current.set(actionKey, uiActionId)
        const confirmed = await confirmHeldBooking({ bookingId, version: bookingVersion, uiActionId })
        confirmActionIdsRef.current.delete(actionKey)
        setSubmitting(false)
        setBookingCode(confirmed.booking_code)
        setBookingAdvisor(confirmed.advisor || null)
        setAccessFlow(null)
        setSuccessCinematic(true)
        addMessage('assistant', 'Xác thực OTP thành công! Lịch đặt lái thử của bạn đã được xác nhận chính thức.')
        return
      }

      const enteredCode = (accessValue.bookingCode || pendingRescheduleIntentRef.current?.bookingCode || '').trim().toLowerCase()
      const targetByCode = enteredCode ? formattedBookings.find((b) => ((b.booking_code || b.bookingCode || '')).toLowerCase() === enteredCode) : null
      const specificTarget = targetByCode

      if (formattedBookings.length > 1 && !specificTarget) {
        setAccessProfile({
          accessToken: verified.access_session_token,
          accessPurpose,
          bookingId: verified.booking_id,
          bookingCode: '',
          bookerName: '',
          driverName: '',
          phone: '',
          email: accessValue.email,
          permissions: verified.permissions || [],
          allowedActions: [],
          vehicleName: '',
          vehicleModelId: '',
          showroomName: '',
          showroomId: '',
          showroomAddress: '',
          advisorName: '',
          advisorPhone: '',
          slotTime: '',
          slotDate: '',
        })
        setExpandedBookingId('')
        setAccessFlow(null)
        dispatchInteraction({ type: InteractionEvent.ACCESS_LIST })
        otpChallengeIdRef.current = ''
        otpCodeRef.current = ''
        addMessage('assistant', `Xác thực thành công. Tôi tìm thấy ${formattedBookings.length} lịch hợp lệ với email này, bạn chọn lịch muốn xem hoặc chỉnh sửa nhé.`)
        return
      }

      if (formattedBookings.length === 0) {
        clearManagementContext({ resetConversation: false })
        addMessage('assistant', 'Bạn đã xác thực thành công, nhưng tôi chưa tìm thấy lịch nào còn hiệu lực với email này.')
        return
      }

      const targetBookingId = specificTarget?.id || formattedBookings[0]?.id || verified.booking_id
      const booking = await getVerifiedBooking({ accessToken: verified.access_session_token, bookingId: targetBookingId })
      const targetProfile = {
        accessToken: verified.access_session_token,
        accessPurpose,
        bookingId: booking.id,
        bookingCode: booking.booking_code || '',
        bookerName: booking.booker?.full_name || '',
        driverName: booking.driver?.full_name || '',
        phone: booking.driver?.phone || booking.booker?.phone || '',
        // The verified email is the intended pre-fill value for booker edits.
        email: accessValue.email || booking.booker?.email || '',
        permissions: verified.permissions || [],
        allowedActions: booking.allowed_actions || [],
        vehicleName: booking.vehicle?.name || '',
        vehicleModelId: booking.vehicle?.id || '',
        showroomName: booking.showroom?.name || '',
        showroomId: booking.showroom?.id || '',
        showroomAddress: booking.showroom?.address || '',
        advisorName: booking.advisor?.full_name || 'Chưa phân công',
        advisorPhone: booking.advisor?.phone || '',
        slotTime: booking.slot_time || '',
        slotDate: booking.slot_date || '',
      }
      setAccessProfile(targetProfile)
      setExpandedBookingId(booking.id)
      setAccessFlow({ phase: isCancellation ? 'confirm_cancel' : 'edit', purpose: accessPurpose, challengeId: '', expiresAt: 0 })
      dispatchInteraction({
        type: isCancellation ? InteractionEvent.ACCESS_CANCEL_CONFIRM : InteractionEvent.ACCESS_EDIT,
      })
      otpChallengeIdRef.current = ''
      otpCodeRef.current = ''
      const isReschedule = accessPurpose === 'reschedule' || Boolean(pendingRescheduleIntentRef.current?.reschedule_target_date || pendingRescheduleIntentRef.current?.reschedule_target_time)
      if (isReschedule) {
        beginTimeReschedule(targetProfile)
      } else {
        addMessage('assistant', isCancellation ? 'Xác thực thành công. Vui lòng kiểm tra phiếu bên dưới và xác nhận nếu bạn muốn hủy lịch.' : 'Bạn đã xác thực thành công. Bạn có thể cập nhật thông tin lịch đã đặt ngay bên dưới.')
      }
    } catch (error) { setAccessError(''); addMessage('assistant', error.message) } finally { setAccessBusy(false) }
  }

  const cancelAccessOtp = () => {
    clearManagementContext({ event: InteractionEvent.CANCEL_ACCESS })
    addMessage('assistant', 'ViVi đã dừng bước xác thực rồi. Khi nào bạn cần xem hoặc chỉnh sửa lịch, bạn cứ nhắn cho ViVi nhé.')
  }
  const closeBookingDetails = () => {
    clearManagementContext({ event: InteractionEvent.CLOSE_BOOKING_DETAILS })
    addMessage('assistant', 'ViVi đã đóng phần quản lý lịch. Bạn có thể tiếp tục xem xe hoặc bắt đầu một yêu cầu khác.')
  }
  const resumeConversation = () => {
    // Nháp tạo trước khi lưu recipient không đủ dữ liệu để hiện lại modal;
    // tiếp tục thẳng với lựa chọn mặc định thay vì chặn người dùng thêm lần nữa.
    if (!recipient) setRecipient('self')
    if (restoredUi.selectedCarId) setSelectedCarId(restoredUi.selectedCarId)
    if (restoredUi.activeView) setActiveView(restoredUi.activeView)
    if (['map', 'schedule'].includes(restoredUi.activeView || activeView)
      && ['choose_showroom', 'choose_slot'].includes(stage)) {
      setMobileSurface('workspace')
    } else {
      setMobileSurface('assistant')
    }
    if (restoredFloatingDemo) {
      setFloatingDemoEnabled(true)
      setFloatingDemoStep(Number(restoredFloatingDemo.step) || 0)
      setFloatingDemoCollapsed(Boolean(restoredFloatingDemo.collapsed))
      floatingDemoContextRef.current = restoredFloatingDemo.isSimulated ? { isSimulated: true } : {}
      setFloatingDemoStatus('Đã tiếp tục lượt demo ở chặng trước đó')
    }
    setResumePending(false)
  }
  const restartConversation = () => {
    window.sessionStorage.removeItem(BOOKING_UI_STATE_KEY)
    resetBookingConversation()
    window.location.reload()
  }

  const selectAccessibleBooking = async (summary) => {
    if (!accessProfile?.accessToken) return
    setAccessBusy(true); setAccessError('')
    try {
      const booking = await getVerifiedBooking({ accessToken: accessProfile.accessToken, bookingId: summary.id })
      const selectedProfile = { ...accessProfile, bookingId: booking.id, bookingCode: booking.booking_code || '', bookerName: booking.booker?.full_name || '', driverName: booking.driver?.full_name || '', phone: booking.driver?.phone || booking.booker?.phone || '', email: accessProfile.email || accessValue.email || booking.booker?.email || '', allowedActions: booking.allowed_actions || [], vehicleName: booking.vehicle?.name || '', vehicleModelId: booking.vehicle?.id || '', showroomName: booking.showroom?.name || '', showroomId: booking.showroom?.id || '', showroomAddress: booking.showroom?.address || '', advisorName: booking.advisor?.full_name || 'Chưa phân công', advisorPhone: booking.advisor?.phone || '', slotTime: booking.slot_time || '', slotDate: booking.slot_date || '' }
      setAccessProfile(selectedProfile)
      setExpandedBookingId(booking.id)
      setAccessFlow({ phase: accessProfile.accessPurpose === 'cancel' ? 'confirm_cancel' : 'edit', purpose: accessProfile.accessPurpose || 'lookup', challengeId: '', expiresAt: 0 })
      dispatchInteraction({ type: accessProfile.accessPurpose === 'cancel' ? InteractionEvent.ACCESS_CANCEL_CONFIRM : InteractionEvent.ACCESS_EDIT })
      return selectedProfile
    } catch (error) { setAccessError(error.message) } finally { setAccessBusy(false) }
  }

  /**
   * Mở popup huỷ lịch NGAY TRONG danh sách tra cứu.
   * Trước đây chỉ vào được popup này khi ngay từ đầu người dùng chọn mục đích "huỷ"; ai đang
   * xem lịch mà muốn huỷ thì phải thoát ra làm lại từ bước xác thực. Dùng lại đúng
   * CancellationConfirmModal đã có, không dựng popup mới.
   */
  const beginAccessibleCancellation = async (summary) => {
    const targetProfile = summary.id === accessProfile?.bookingId
      ? accessProfile
      : await selectAccessibleBooking(summary)
    if (!targetProfile) return
    setAccessError('')
    setAccessFlow({ phase: 'confirm_cancel', purpose: 'cancel', challengeId: '', expiresAt: 0 })
    dispatchInteraction({ type: InteractionEvent.ACCESS_CANCEL_CONFIRM })
  }

  /**
   * Thoát luồng đổi giờ, quay về danh sách lịch đã đặt.
   * Trước đây vào tới bảng chọn giờ mới là KẸT: không có nút lùi, muốn xem lịch khác phải
   * tải lại trang và xác thực OTP từ đầu.
   */
  const exitReschedule = () => {
    setRescheduleState(null)
    setAccessError('')
    setAccessFlow({ phase: 'edit', purpose: accessProfile?.accessPurpose || 'lookup', challengeId: '', expiresAt: 0 })
    dispatchInteraction({ type: InteractionEvent.ACCESS_EDIT })
  }

  /**
   * Bấm "Giữ lại lịch" trong popup huỷ thì QUAY VỀ danh sách, không thoát hẳn.
   * Dùng closeBookingDetails như trước sẽ xoá sạch ngữ cảnh quản lý lịch — người dùng chỉ
   * lỡ mở nhầm popup mà bị đá ra khỏi cả luồng tra cứu, phải xác thực OTP lại từ đầu.
   */
  const dismissCancellation = () => {
    setAccessError('')
    setAccessFlow({ phase: 'edit', purpose: accessProfile?.accessPurpose || 'lookup', challengeId: '', expiresAt: 0 })
    dispatchInteraction({ type: InteractionEvent.ACCESS_EDIT })
  }

  const changeAccessProfile = (field, value) => setAccessProfile((current) => ({ ...current, [field]: value }))
  const openRescheduleConfirmation = () => {
    if (rescheduleState?.step !== 'pending') return
    setRescheduleState((current) => ({ ...current, step: 'confirm' }))
    dispatchInteraction({ type: InteractionEvent.RESCHEDULE_CONFIRM })
  }
  const saveAccessProfile = async (event) => {
    event.preventDefault()
    if (!accessProfile) return
    if (rescheduleState?.step === 'pending') {
      openRescheduleConfirmation()
      return
    }
    setAccessBusy(true); setAccessError('')
    try {
      await updateVerifiedBooking({
        bookingId: accessProfile.bookingId,
        accessToken: accessProfile.accessToken,
        bookerPatch: { full_name: accessProfile.bookerName, phone: accessProfile.phone, email: accessProfile.email },
        // Chỉ sửa thông tin người đặt trên panel khách hàng; không đổi người lái thử của lịch hiện có.
        driverPatch: null,
        driverSameAsBooker: false,
      })
      clearManagementContext({ event: InteractionEvent.CLOSE_BOOKING_DETAILS })
      addMessage('assistant', 'ViVi đã cập nhật thông tin đặt lịch của bạn.')
    } catch (error) { setAccessError(error.message) } finally { setAccessBusy(false) }
  }

  const confirmCancellation = async () => {
    if (!accessProfile) return
    setAccessBusy(true); setAccessError('')
    try {
      const cancelled = await cancelVerifiedBooking({ bookingId: accessProfile.bookingId, accessToken: accessProfile.accessToken })
      // Chỉ báo đã huỷ khi BACKEND nói là đã huỷ. Trước đây bỏ qua hoàn toàn response nên
      // bất kỳ phản hồi thành công một phần nào cũng bị hiển thị thành "đã huỷ xong".
      if (cancelled?.booking_status && cancelled.booking_status !== 'cancelled') {
        setAccessError(`Lịch chưa được huỷ (trạng thái hiện tại: ${cancelled.booking_status}). ViVi thử lại hoặc gọi hotline giúp bạn nhé.`)
        return
      }
      clearManagementContext()
      addMessage('assistant', `ViVi đã hủy lịch ${accessProfile.bookingCode}. Khung giờ đã được mở lại.`)
    } catch (error) { setAccessError(error.message) } finally { setAccessBusy(false) }
  }

  const loadRescheduleSlots = async (car, showroom, targetProfile = accessProfile) => {
    setAccessBusy(true); setAccessError('')
    try {
      const result = await searchBookingOptions({ vehicleModel: car.name, showroomId: showroom.id })
      const slots = result.slots || []
      const availableSlots = slots.filter((slot) => slot.status === 'available')
      const targetIntent = pendingRescheduleIntentRef.current

      if (targetIntent?.reschedule_target_date && availableSlots.length > 0 && targetProfile?.bookingId && targetProfile?.accessToken) {
        const targetDate = targetIntent.reschedule_target_date
        const targetTime = targetIntent.reschedule_target_time
        const dateSlots = availableSlots.filter((s) => {
          const slotDateTime = getVietnamSlotDateTime(s.start_at || s.startAt)
          return slotDateTime?.date === targetDate
        })

        if (dateSlots.length > 0) {
          let bestSlot = dateSlots[0]
          if (targetTime) {
            const [tH, tM] = targetTime.split(':').map(Number)
            const targetMinutes = (tH || 0) * 60 + (tM || 0)
          let minDiff = Infinity
          for (const s of dateSlots) {
            const slotDateTime = getVietnamSlotDateTime(s.start_at || s.startAt)
            if (!slotDateTime) continue
            const sMinutes = slotDateTime.minutes
              const diff = Math.abs(sMinutes - targetMinutes)
              if (diff < minDiff) {
                minDiff = diff
                bestSlot = s
              }
            }
          }

          if (bestSlot) {
            pendingRescheduleIntentRef.current = null
            const held = await holdVerifiedReschedule({ bookingId: targetProfile.bookingId, slotId: bestSlot.id, accessToken: targetProfile.accessToken })
            setRescheduleState({ step: 'pending', car, showroom, slots, slot: bestSlot, newBookingId: held.booking_id })
            setRescheduleSecondsLeft(Math.max(0, Math.ceil((new Date(held.hold_expires_at).getTime() - Date.now()) / 1000)))
            setExpandedBookingId(targetProfile.bookingId)
            setMobileSurface('workspace')
            dispatchInteraction({ type: InteractionEvent.RESCHEDULE_CONFIRM })
            const startsAt = new Date(bestSlot.start_at || bestSlot.startAt)
            const timeStr = startsAt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false })
            const dateStr = new Intl.DateTimeFormat('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit' }).format(startsAt)
            addMessage('assistant', `ViVi đã tìm thấy khung giờ ${timeStr} (${dateStr}) phù hợp nhất với yêu cầu và đã giữ tạm trong 5 phút. Bạn kiểm tra phiếu bên cạnh và bấm “Xác nhận đổi lịch” nhé!`)
            return
          }
        } else {
          pendingRescheduleIntentRef.current = null
          setRescheduleState({ step: 'schedule', car, showroom, slots })
          dispatchInteraction({ type: InteractionEvent.RESCHEDULE_SLOT })
          const [, tMonth, tDay] = targetDate.split('-')
          addMessage('assistant', `Ngày ${tDay}/${tMonth} hiện chưa có khung giờ trống tại ${showroom.name}. ViVi đã mở bảng lịch các ngày lân cận để bạn dễ dàng chọn lại khung giờ phù hợp nhé!`)
          return
        }
      }

      if (slots.some((slot) => slot.status === 'available')) {
        setRescheduleState({ step: 'schedule', car, showroom, slots })
        dispatchInteraction({ type: InteractionEvent.RESCHEDULE_SLOT })
      }
      else {
        const alternatives = await searchBookingOptions({ vehicleModel: car.name })
        setRescheduleState({ step: 'showroom', car, showrooms: alternatives.showrooms || [] })
        dispatchInteraction({ type: InteractionEvent.RESCHEDULE_SHOWROOM })
      }
    } catch (error) { setAccessError(error.message) } finally { setAccessBusy(false) }
  }
  const beginTimeReschedule = (targetProfile = accessProfile) => {
    const car = cars.find((item) => item.id === targetProfile?.vehicleModelId)
      || cars.find((item) => normalizeVehicleName(item.name) === normalizeVehicleName(targetProfile?.vehicleName))
    if (car && targetProfile?.showroomId) {
      setSelectedCarId(car.id)
      setWorkspaceHidden(false)
      setMobileSurface('workspace')
      setAccessFlow((current) => current ? { ...current, phase: 'edit', purpose: 'reschedule' } : { phase: 'edit', purpose: 'reschedule', challengeId: '', expiresAt: 0 })
      dispatchInteraction({ type: InteractionEvent.START_RESCHEDULE })
      loadRescheduleSlots(car, { id: targetProfile.showroomId, name: targetProfile.showroomName }, targetProfile)
    } else setAccessError('ViVi chưa xác định được mẫu xe hoặc showroom của lịch này, nên tạm thời chưa đổi lịch được cho bạn.')
  }
  const beginAccessibleReschedule = async (summary) => {
    const targetProfile = summary.id === accessProfile?.bookingId ? accessProfile : await selectAccessibleBooking(summary)
    if (targetProfile) beginTimeReschedule(targetProfile)
  }
  const holdReschedule = async (slot) => {
    setAccessBusy(true); setAccessError('')
    try {
      const held = await holdVerifiedReschedule({ bookingId: accessProfile.bookingId, slotId: slot.id, accessToken: accessProfile.accessToken })
      // KHÔNG ghi đè slotTime/slotDate của accessProfile ở bước này. Lịch cũ vẫn đang là lịch
      // THẬT cho tới khi bấm xác nhận — giữ chỗ mới có thể hết hạn hoặc người dùng đổi ý.
      // Bản cũ ghi đè ngay tại đây nên phiếu hiện giờ mới trong khi backend vẫn giữ giờ cũ,
      // và nếu thoát giữa chừng thì người dùng không còn thấy giờ hẹn thật của mình nữa.
      // Giờ mới đã được RescheduleConfirmModal hiển thị từ chính `state.slot`.
      setRescheduleState((current) => ({ ...current, step: 'pending', slot, newBookingId: held.booking_id }))
      setRescheduleSecondsLeft(Math.max(0, Math.ceil((new Date(held.hold_expires_at).getTime() - Date.now()) / 1000)))
      setExpandedBookingId(accessProfile.bookingId)
      setMobileSurface('workspace')
      dispatchInteraction({ type: InteractionEvent.RESCHEDULE_CONFIRM })
      addMessage('assistant', 'ViVi đã giữ tạm khung giờ mới và cập nhật trên phiếu. Bạn bấm “Cập nhật thông tin” để kiểm tra, xác nhận toàn bộ lịch.')
    } catch (error) { setAccessError(error.message) } finally { setAccessBusy(false) }
  }
  const confirmReschedule = async () => {
    setAccessBusy(true); setAccessError('')
    try {
      // Đổi lịch CHỈ dời khung giờ. Bản cũ gọi thêm updateVerifiedBooking() ngay trước đó và
      // gây hỏng dữ liệu thật sự: nó gán `phone`/`email` của NGƯỜI ĐẶT cho người lái, nên ai
      // đặt hộ với liên hệ riêng (xem Batch 6) mà đổi lịch là mất sạch liên hệ của người lái.
      // Nó còn đoán "hai người là một" bằng cách SO SÁNH TÊN — hai người trùng tên là sai ngay.
      // Backend không đòi cập nhật hồ sơ trước khi dời lịch: confirm_reschedule chỉ kiểm tra
      // trạng thái hai booking và hạn giữ chỗ (services/booking/management.py).
      await confirmVerifiedReschedule({ bookingId: accessProfile.bookingId, newBookingId: rescheduleState.newBookingId, accessToken: accessProfile.accessToken })
      const startsAt = new Date(rescheduleState.slot.start_at)
      setAccessProfile((current) => ({ ...current, bookingId: rescheduleState.newBookingId, slotTime: startsAt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false }), slotDate: new Intl.DateTimeFormat('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit' }).format(startsAt) }))
      clearManagementContext({ event: InteractionEvent.FINISH_RESCHEDULE })
      addMessage('assistant', `ViVi đã đổi lịch thành công. Mã lịch ${accessProfile.bookingCode} được giữ nguyên. ViVi đã gửi thông tin lịch mới qua email.`)
    } catch (error) { setAccessError(error.message) } finally { setAccessBusy(false) }
  }

  useEffect(() => {
    if (resendSecondsLeft <= 0 && accessSecondsLeft <= 0) return undefined
    const timer = window.setInterval(() => {
      setAccessSecondsLeft((value) => Math.max(0, value - 1))
      setResendSecondsLeft((value) => Math.max(0, value - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [resendSecondsLeft, accessSecondsLeft])

  useEffect(() => {
    if (!rescheduleState || rescheduleState.step !== 'pending') return undefined
    if (rescheduleSecondsLeft <= 0) {
      setRescheduleState(null)
      dispatchInteraction({ type: InteractionEvent.ACCESS_EDIT })
      addMessage('assistant', 'Thời gian ViVi giữ tạm khung giờ mới đã hết. Lịch cũ của bạn vẫn được giữ nguyên, bạn yên tâm nhé.')
      return undefined
    }
    const timer = window.setInterval(() => setRescheduleSecondsLeft((value) => Math.max(0, value - 1)), 1000)
    return () => window.clearInterval(timer)
  }, [rescheduleState, rescheduleSecondsLeft])

  const changePerson = (field, value) => {
    setPerson((current) => ({ ...current, [field]: value }))
    setFormErrors((current) => ({ ...current, [field]: '' }))
  }

  const inlineOtpCode = inlineOtpDigits.join('')
  const isInlineOtpComplete = inlineOtpCode.length === 6

  const handleInlineOtpDigit = (index, raw) => {
    const digit = raw.replace(/\D/g, '').slice(-1)
    const nextDigits = inlineOtpDigits.map((curr, i) => (i === index ? digit : curr))
    setInlineOtpDigits(nextDigits)
    setInlineOtpError('')
    if (digit && index < 5) {
      document.getElementById(`review-otp-${index + 1}`)?.focus()
    }
  }

  const handleInlineOtpKeyDown = (index, event) => {
    if (event.key === 'Backspace') {
      if (!inlineOtpDigits[index] && index > 0) {
        event.preventDefault()
        const prevIndex = index - 1
        const nextDigits = inlineOtpDigits.map((curr, i) => (i === prevIndex ? '' : curr))
        setInlineOtpDigits(nextDigits)
        setInlineOtpError('')
        document.getElementById(`review-otp-${prevIndex}`)?.focus()
      }
    }
  }

  const handleInlineOtpPaste = (event) => {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (pasted) {
      event.preventDefault()
      const pastedArray = Array.from({ length: 6 }, (_, i) => pasted[i] || '')
      setInlineOtpDigits(pastedArray)
      setInlineOtpError('')
      const nextFocus = Math.min(pasted.length, 6) - 1
      document.getElementById(`review-otp-${nextFocus}`)?.focus()
      if (pasted.length === 6 && !submitting) {
        confirmFinalBooking(pasted)
      }
    }
  }

  const requestInlineOtp = async (emailToUse = person.email) => {
    if (!emailToUse || !EMAIL_PATTERN.test(emailToUse.trim())) return
    setInlineOtpBusy(true)
    setInlineOtpError('')
    try {
      const result = await requestBookingAccess({
        bookingCode: bookingId,
        email: emailToUse.trim(),
        purpose: 'confirm_booking',
        preferredChannel: 'email',
      })
      setInlineOtpChallengeId(result.challenge_id)
      otpChallengeIdRef.current = result.challenge_id
      setResendSecondsLeft(result.retry_after_seconds || 60)
      if (result.is_mock && result.otp_code) {
        setInlineOtpMock(result.otp_code)
      }
    } catch (err) {
      setInlineOtpError(accessErrorMessage(err) || 'Chưa gửi được mã OTP. Bạn bấm "Gửi lại OTP" giúp tôi nhé.')
    } finally {
      setInlineOtpBusy(false)
    }
  }

  const confirmFinalBooking = async (overrideCode) => {
    const codeToVerify = typeof overrideCode === 'string' ? overrideCode : inlineOtpCode
    if (codeToVerify.length !== 6 || submitting || bookingMutationRef.current) return
    const challengeId = inlineOtpChallengeId || otpChallengeIdRef.current
    if (!challengeId) {
      setInlineOtpError('Phiên xác thực chưa sẵn sàng. Bấm "Gửi lại OTP" giúp tôi nhé.')
      return
    }
    bookingMutationRef.current = true
    setSubmitting(true)
    setInlineOtpError('')
    try {
      // 1. Verify 6-digit OTP
      const verified = await verifyBookingAccess({
        challengeId,
        otpCode: codeToVerify,
      })

      if (!verified || !verified.access_session_token) {
        throw new Error('Mã OTP chưa chính xác, bạn kiểm tra lại nhé.')
      }

      // 2. Confirm booking
      const actionKey = `${bookingId}:${bookingVersion}`
      const uiActionId = confirmActionIdsRef.current.get(actionKey) || actionId('confirm')
      confirmActionIdsRef.current.set(actionKey, uiActionId)
      const confirmed = await confirmHeldBooking({ bookingId, version: bookingVersion, uiActionId })
      confirmActionIdsRef.current.delete(actionKey)
      setSubmitting(false)
      setBookingCode(confirmed.booking_code)
      setBookingAdvisor(confirmed.advisor || null)
      setHoldExpiresAt(null)
      setTimeLeft('')
      setSuccessCinematic(true)

      try {
        const lastConfirmedData = {
          car: selectedCar,
          showroom: selectedShowroom,
          slot: selectedSlot,
          bookingCode: confirmed.booking_code,
          advisor: confirmed.advisor || null,
          person,
        }
        window.sessionStorage.setItem('LAST_CONFIRMED_BOOKING', JSON.stringify(lastConfirmedData))
      } catch (e) {
        console.error('Lỗi khi lưu LAST_CONFIRMED_BOOKING:', e)
      }
    } catch (err) {
      setSubmitting(false)
      if (err.code === 'HOLD_EXPIRED' || err.code === 'SLOT_NO_LONGER_AVAILABLE') {
        setInlineOtpDigits(['', '', '', '', '', ''])
        setInlineOtpError('')
        setInlineOtpChallengeId('')
        setPendingSlot(null)
        setSelectedSlot(null)
        setBookingId('')
        setBookingVersion(0)
        setStage('choose_slot')
        showMobileWorkspace('schedule')
        addMessage('assistant', 'Thời gian giữ tạm khung giờ này đã hết hạn. Bạn vui lòng chọn lại một khung giờ khác nhé.')
        return
      }
      setInlineOtpError(accessErrorMessage(err) || 'Mã OTP chưa đúng, bạn kiểm tra lại giúp tôi nhé.')
    } finally {
      bookingMutationRef.current = false
      setSubmitting(false)
    }
  }

  const submitPerson = async (event) => {
    event.preventDefault()
    if (bookingMutationRef.current || submitting) return
    if (!bookingId || !selectedSlot) {
      setBackendError('Chưa có khung giờ được giữ. Bạn vui lòng chọn và xác nhận khung giờ trước.')
      return
    }
    const errors = {}
    if (person.bookingName.trim().length < 2) errors.bookingName = 'Bạn vui lòng cho tôi biết tên người đứng ra đặt lịch.'
    if (recipient === 'other' && person.driverName.trim().length < 2) errors.driverName = 'Bạn vui lòng cho tôi biết tên người sẽ trực tiếp lái thử.'
    if (person.phone.trim() && !PHONE_PATTERN.test(person.phone.trim())) errors.phone = 'Số điện thoại này chưa đúng định dạng Việt Nam, bạn kiểm tra lại giúp tôi nhé.'
    if (!EMAIL_PATTERN.test(person.email.trim())) errors.email = 'Bạn vui lòng nhập email, và nhập đúng định dạng để tôi gửi xác nhận lịch.'

    if (recipient === 'other' && person.driverSameContact === false) {
      if (!EMAIL_PATTERN.test(person.driverEmail.trim())) {
        errors.driverEmail = 'Bạn vui lòng nhập email của người lái thử, và nhập đúng định dạng.'
      }
      if (person.driverPhone.trim() && !PHONE_PATTERN.test(person.driverPhone.trim())) {
        errors.driverPhone = 'Số điện thoại của người lái thử chưa đúng định dạng, bạn kiểm tra lại nhé.'
      }
    }

    if (!person.hasLicense) errors.hasLicense = 'Bạn vui lòng xác nhận người lái thử có giấy phép lái xe phù hợp trước khi tiếp tục.'
    setFormErrors(errors)
    if (Object.keys(errors).length) return

    setBackendError('')
    bookingMutationRef.current = true
    setSubmitting(true)
    try {
      const saved = await saveBookingCustomer({ bookingId, version: bookingVersion, recipient, person })
      setBookingVersion(saved.version)
      setStage('review')
      setActiveView('ticket')
      setInlineOtpDigits(['', '', '', '', '', ''])
      setInlineOtpError('')
      addMessage('user', 'Tôi đã hoàn tất thông tin người lái.')
      reply('ViVi đã lưu phiếu tạm cho bạn. Mã OTP 6 chữ số vừa được gửi qua email. Bạn nhập mã 6 số vào ô bên phải để kích hoạt nút "Xác nhận đặt lịch" nhé.')
      await requestInlineOtp(person.email)
    } catch (error) {
      reply(`ViVi chưa lưu được thông tin của bạn: ${error.message}`)
    } finally {
      bookingMutationRef.current = false
      setSubmitting(false)
    }
  }

  const submitBooking = async () => {
    setSubmitting(true)
    setAccessError('')
    try {
      const result = await requestBookingAccess({
        bookingCode: bookingId,
        email: person.email,
        purpose: 'confirm_booking',
        preferredChannel: 'email',
      })
      otpChallengeIdRef.current = result.challenge_id
      const expiresAt = result.expires_at ? new Date(result.expires_at).getTime() : Date.now() + 600000
      setAccessFlow({
        phase: 'verify',
        purpose: 'confirm_booking',
        challengeId: result.challenge_id,
        expiresAt,
      })
      dispatchInteraction({ type: InteractionEvent.ACCESS_VERIFY })
      setAccessValue((current) => ({ ...current, email: person.email, otpCode: '' }))
      setAccessSecondsLeft(Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000)))
      setResendSecondsLeft(result.retry_after_seconds || 60)

      const mockOtp = result.is_mock ? result.otp_code : ''
      addMessage(
        'assistant',
        mockOtp
          ? `Mã OTP xác nhận đặt lịch của bạn là **${mockOtp}**. Nhập mã này để chốt lịch chính thức.`
          : `ViVi đã gửi mã OTP xác nhận đặt lịch đến email **${person.email}**. Bạn vui lòng nhập mã để chốt lịch nhé.`,
      )
    } catch (error) {
      reply(`Chưa thể gửi mã OTP xác nhận: ${error.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  const ensureFloatingDemoRun = (runId) => {
    if (!floatingDemoMountedRef.current || floatingDemoRunRef.current !== runId) {
      throw new Error('Demo đã được bắt đầu lại.')
    }
  }

  // A short beat makes each visual change perceptible, while the controller keeps
  // moving without requiring another click from the presenter.
  const waitFloatingDemo = (runId, milliseconds = FLOATING_DEMO_STEP_DELAY_MS) => new Promise((resolve) => {
    const finish = () => {
      window.clearTimeout(timer)
      floatingDemoDelayWaitersRef.current = floatingDemoDelayWaitersRef.current.filter((waiter) => waiter !== finish)
      resolve()
    }
    const timer = window.setTimeout(finish, milliseconds)
    floatingDemoDelayWaitersRef.current.push(finish)
  }).then(() => ensureFloatingDemoRun(runId))

  const getFloatingDemoLocation = () => new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve({ location: null, reason: 'Trình duyệt không hỗ trợ vị trí' })
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ location: { latitude: coords.latitude, longitude: coords.longitude }, reason: '' }),
      (error) => {
        const reason = error.code === error.PERMISSION_DENIED
          ? 'Quyền vị trí đang bị chặn'
          : error.code === error.TIMEOUT
            ? 'Lấy vị trí bị quá thời gian chờ'
            : 'Không xác định được vị trí hiện tại'
        resolve({ location: null, reason })
      },
      { enableHighAccuracy: false, maximumAge: 5 * 60 * 1000, timeout: 8000 },
    )
  })

  const waitForFloatingDemoResume = async (runId) => {
    while (floatingDemoPausedRef.current) {
      await new Promise((resolve) => floatingDemoPauseWaitersRef.current.push(resolve))
      ensureFloatingDemoRun(runId)
    }
  }

  // Deterministic demo copy, not an LLM request. The visible composer and
  // typing state make each scripted step read like a genuine chat exchange.
  const beginFloatingDemoTurn = async (step, text, runId) => {
    setDraft(text)
    await waitFloatingDemo(runId, 850)
    setDraft('')
    addMessage('user', text, { floatingDemoStep: step })
    setAgentTyping(true)
    await waitFloatingDemo(runId, 700)
  }

  const finishFloatingDemoTurn = (step, text) => {
    setAgentTyping(false)
    addMessage('assistant', text, { floatingDemoStep: step })
  }

  const runFloatingDemoStep = async (step, runId) => {
    ensureFloatingDemoRun(runId)
    if (step === 1) {
      await beginFloatingDemoTurn(step, 'Tôi đặt lịch lái thử cho chính tôi.', runId)
      setRecipient('self')
      setResumePending(false)
      setWorkspaceHidden(false)
      setFloatingDemoStatus('Đã chọn người đặt: chính tôi')
      finishFloatingDemoTurn(step, 'Được rồi, ViVi sẽ đồng hành cùng bạn chọn mẫu xe và lịch lái thử phù hợp.')
      return
    }

    if (step === 2) {
      await beginFloatingDemoTurn(step, 'Tôi muốn lái thử VF 9.', runId)
      const car = cars.find((item) => item.id === 'vf9')
      if (!car) throw new Error('Catalog hiện chưa có mẫu VF 9 để trình diễn.')
      setSelectedCarId(car.id)
      resetSelectionForVehicleChange()
      setStage('need_address')
      setActiveView('car')
      finishFloatingDemoTurn(step, 'ViVi đã chọn VF 9. Mình sẽ tìm showroom còn lịch cho buổi lái thử.')
      setFloatingDemoStatus('Đã chọn VF 9')
      floatingDemoContextRef.current = { car }
      return
    }

    const context = floatingDemoContextRef.current
    if (!context.car) throw new Error('Hãy chạy bước chọn VF 9 trước.')

    if (step === 3) {
      await beginFloatingDemoTurn(step, 'Dùng vị trí hiện tại để tìm showroom gần tôi.', runId)
      setFloatingDemoStatus('Đang lấy vị trí hiện tại')
      const locationResult = await getFloatingDemoLocation()
      const location = locationResult.location
      ensureFloatingDemoRun(runId)
      let result
      if (location) {
        result = await searchFloatingDemoOptions({
          vehicleModel: context.car.name,
          showroomLimit: 12,
          ...location,
        })
      } else {
        // Không có quyền vị trí thì không thể nói showroom nào là "gần nhất".
        // Demo ưu tiên Landmark 81 để luôn có một phương án dễ nhận biết.
        try {
          result = await searchFloatingDemoOptions({ vehicleModel: context.car.name, showroomQuery: 'Landmark 81', showroomLimit: 12 })
        } catch (error) {
          if (error.code !== 'SHOWROOM_NOT_FOUND') throw error
          result = await searchFloatingDemoOptions({ vehicleModel: context.car.name, showroomLimit: 12 })
        }
      }
      ensureFloatingDemoRun(runId)
      const showrooms = mapShowrooms(result.showrooms || [], context.car.id)
      if (!showrooms.length) throw new Error('Không tìm thấy showroom có VF 9 để trình diễn.')
      context.showrooms = showrooms
      context.location = location
      setNearbyShowrooms(showrooms)
      setUserLocation(location)
      setAddress({ province: '', detail: location ? 'Vị trí hiện tại' : 'Chưa cấp quyền vị trí' })
      setStage('choose_showroom')
      setActiveView('map')
      setFloatingDemoStatus(location ? `Đã tìm thấy ${showrooms.length} showroom gần bạn` : `${locationResult.reason} · ưu tiên Landmark 81`)
      finishFloatingDemoTurn(step, location
        ? `ViVi đã lấy vị trí hiện tại và tìm thấy ${showrooms.length} showroom còn lịch.`
        : `${locationResult.reason}. ViVi ưu tiên Landmark 81 cho lượt demo này.`)
      return
    }

    if (step === 4) {
      const showroom = context.showrooms[0]
      if (!showroom) throw new Error('Hãy lấy vị trí hiện tại trước.')
      await beginFloatingDemoTurn(step, 'Chọn showroom gần nhất có lịch lái thử VF 9.', runId)
      const result = await searchFloatingDemoOptions({ vehicleModel: context.car.name, showroomId: showroom.id })
      ensureFloatingDemoRun(runId)
      const groupedSlots = groupSlots(result.slots || [])
      const rawSlot = (result.slots || [])
        .filter((slot) => slot.status === 'available' && new Date(slot.start_at).getTime() > Date.now())
        .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())[0]
      const earliestSlot = rawSlot ? findSlotById(groupedSlots, rawSlot.id) : null
      if (!earliestSlot) throw new Error(`${showroom.name} hiện chưa có khung giờ trống.`)
      context.showroom = showroom
      context.slots = groupedSlots
      context.slot = earliestSlot
      setShowroomId(showroom.id)
      setSlots(groupedSlots)
      setPendingSlot(null)
      setSelectedSlot(null)
      setStage('choose_slot')
      setActiveView('schedule')
      setFloatingDemoStatus(`Đã chọn ${showroom.name} · đã tải ${result.slots?.length || 0} khung giờ`)
      finishFloatingDemoTurn(step, `ViVi đã chọn showroom gần nhất: ${showroom.name}. Lịch trống đã được hiển thị.`)
      return
    }

    if (step === 5) {
      if (!context.slot || !context.showroom) throw new Error('Hãy chọn showroom trước.')
      await beginFloatingDemoTurn(step, 'Chọn giúp tôi khung giờ trống sớm nhất.', runId)
      setNearbyShowrooms(context.showrooms)
      setShowroomId(context.showroom.id)
      setSlots(context.slots || [])
      setPendingSlot(context.slot)
      setSelectedSlot(null)
      setConfirmSlotOpen(false)
      setStage('choose_slot')
      setActiveView('schedule')
      // The floating bar is a showcase, not a booking channel: never lock a
      // real slot or create a record that later needs destructive cleanup.
      context.isSimulated = true
      context.bookingId = `floating-demo-${runId}`
      context.bookingVersion = 1
      setBookingId(context.bookingId)
      setBookingVersion(1)
      setHoldExpiresAt(null)
      setSelectedSlot(context.slot)
      setPendingSlot(null)
      setFloatingDemoStatus('Đã chọn giờ gần nhất và mô phỏng giữ chỗ')
      finishFloatingDemoTurn(step, `ViVi đã chọn ${context.slot.time} · ${context.slot.dateLabel} và mô phỏng giữ chỗ. Không có lịch thật nào được tạo.`)
      return
    }

    if (step === 6) {
      if (!context.bookingId || !context.bookingVersion) throw new Error('Hãy giữ chỗ trước khi lưu hồ sơ.')
      await beginFloatingDemoTurn(step, 'Tôi đã điền xong thông tin người lái thử.', runId)
      setFloatingDemoStatus('Đang điền hồ sơ mẫu')
      setPerson(DEMO_PERSONA)
      // Keep the actual form visible for a full demo beat. It is read-only in
      // Demo mode, so the presenter can see the persona without submitting it.
      setStage('collect_info')
      setActiveView('schedule')
      finishFloatingDemoTurn(step, 'ViVi đã điền hồ sơ người lái mẫu. Bạn có thể xem thông tin và xác nhận GPLX ngay bên dưới.')
      setFloatingDemoStatus('Đã điền hồ sơ người lái mẫu')
      return
    }

    if (step === 7) {
      if (!context.bookingId || !context.bookingVersion) throw new Error('Phiếu demo chưa sẵn sàng để xác nhận.')
      await beginFloatingDemoTurn(step, 'Xác nhận phiếu demo.', runId)
      setFloatingDemoStatus('Đang xác nhận phiếu demo')
      const demoCode = `DEMO-${String(Date.now()).slice(-6)}`
      setBookingCode(demoCode)
      setBookingAdvisor(null)
      setSuccessCinematic(true)
      finishFloatingDemoTurn(step, 'ViVi đang hoàn tất phiếu demo của bạn.')
      setFloatingDemoStatus('Hoàn tất trình diễn · không tạo lịch thật')
      return
    }
  }

  const advanceFloatingDemo = async () => {
    if (floatingDemoBusy || (floatingDemoRunning && !floatingDemoPaused) || floatingDemoStep >= 7) return
    if (floatingDemoRunning && floatingDemoPaused) {
      floatingDemoRunRef.current += 1
      floatingDemoPausedRef.current = false
      floatingDemoPauseWaitersRef.current.splice(0).forEach((resolve) => resolve())
      setFloatingDemoRunning(false)
      setFloatingDemoPaused(false)
    }
    const runId = floatingDemoRunRef.current || 1
    if (!floatingDemoRunRef.current) floatingDemoRunRef.current = runId
    const nextStep = floatingDemoStep + 1
    setFloatingDemoBusy(true)
    try {
      await runFloatingDemoStep(nextStep, runId)
      ensureFloatingDemoRun(runId)
      setFloatingDemoStep(nextStep)
    } catch (error) {
      if (floatingDemoRunRef.current === runId) setFloatingDemoStatus(`${error.message || 'Demo chưa hoàn tất, bạn thử lại nhé.'}${error.code ? ` · ${error.code}` : ''}`)
    } finally {
      if (floatingDemoRunRef.current === runId) {
        setFloatingDemoBusy(false)
        setAgentTyping(false)
      }
    }
  }

  const autoPlayFloatingDemo = async () => {
    if (floatingDemoRunning) return
    // Resume after Lùi/Tiến keeps the visual checkpoint and its transcript.
    // A completed run is the only case where the primary button starts fresh.
    const startsFresh = floatingDemoStep === 0 || floatingDemoStep >= 7
    const startingStep = startsFresh ? 0 : floatingDemoStep
    const runId = floatingDemoRunRef.current + 1
    floatingDemoRunRef.current = runId
    if (startsFresh) {
      // A brand-new showcase must not inherit a visitor conversation, but a
      // resume must never erase its already-presented scenes.
      resetBookingConversation()
      setMessages([])
      setFloatingDemoLogs([])
      setFloatingDemoStep(0)
      floatingDemoContextRef.current = {}
    }
    floatingDemoPausedRef.current = false
    setFloatingDemoPaused(false)
    setFloatingDemoRunning(true)
    setFloatingDemoStatus(startsFresh ? 'Đang bắt đầu luồng chuẩn' : `Đang tiếp tục từ chặng ${startingStep + 1}`)
    try {
      let step = startingStep + 1
      let retriesForStep = 0
      while (step <= 7) {
        await waitForFloatingDemoResume(runId)
        setFloatingDemoBusy(true)
        try {
          await runFloatingDemoStep(step, runId)
        } catch (error) {
          ensureFloatingDemoRun(runId)
          const code = String(error?.code || '')
          const slotChanged = step >= 5 && (
            code === 'SLOT_UNAVAILABLE'
            || code === 'SLOT_NO_LONGER_AVAILABLE'
            || code === 'HOLD_EXPIRED'
          )

          // A real-time slot can disappear between the search and hold/confirm
          // calls. Re-select the nearest available slot and continue automatically
          // instead of leaving the presenter at a dead end.
          if (slotChanged) {
            setFloatingDemoStatus('Khung giờ vừa thay đổi · đang chọn giờ gần nhất khác')
            await runFloatingDemoStep(5, runId)
            ensureFloatingDemoRun(runId)
            setFloatingDemoStep(5)
            retriesForStep = 0
            step = 5
            setFloatingDemoBusy(false)
            await waitFloatingDemo(runId)
            continue
          }

          // Network and service errors are normally transient. Retry each current
          // step once before surfacing the failure in the demo bar.
          if (error?.retryable && retriesForStep < 1) {
            retriesForStep += 1
            setFloatingDemoStatus('Kết nối chậm · đang thử lại tự động')
            setFloatingDemoBusy(false)
            await waitFloatingDemo(runId, 1200)
            continue
          }
          throw error
        }
        ensureFloatingDemoRun(runId)
        setFloatingDemoStep(step)
        setFloatingDemoBusy(false)
        if (step < 7) await waitFloatingDemo(runId)
        step += 1
        retriesForStep = 0
      }
    } catch (error) {
      if (floatingDemoRunRef.current === runId) setFloatingDemoStatus(`${error.message || 'Demo chưa hoàn tất, bạn thử lại nhé.'}${error.code ? ` · ${error.code}` : ''}`)
    } finally {
      if (floatingDemoRunRef.current === runId) {
        setFloatingDemoBusy(false)
        setFloatingDemoRunning(false)
        setFloatingDemoPaused(false)
        setAgentTyping(false)
      }
    }
  }

  const toggleFloatingDemoPause = () => {
    if (!floatingDemoRunning) return autoPlayFloatingDemo()
    floatingDemoPausedRef.current = !floatingDemoPausedRef.current
    setFloatingDemoPaused(floatingDemoPausedRef.current)
    setFloatingDemoStatus(floatingDemoPausedRef.current ? 'Đã tạm dừng sau thao tác hiện tại' : 'Đang tiếp tục luồng chuẩn')
    if (!floatingDemoPausedRef.current) {
      floatingDemoPauseWaitersRef.current.splice(0).forEach((resolve) => resolve())
    }
  }

  const rewindFloatingDemo = async () => {
    if (floatingDemoBusy || (floatingDemoRunning && !floatingDemoPaused) || floatingDemoStep <= 0) return
    if (floatingDemoRunning && floatingDemoPaused) {
      floatingDemoRunRef.current += 1
      floatingDemoPausedRef.current = false
      floatingDemoPauseWaitersRef.current.splice(0).forEach((resolve) => resolve())
      setFloatingDemoRunning(false)
      setFloatingDemoPaused(false)
    }
    const targetStep = floatingDemoStep - 1
    const heldBookingId = bookingId || floatingDemoContextRef.current.bookingId
    if (targetStep < 5 && heldBookingId && !bookingCode && !floatingDemoContextRef.current.isSimulated) {
      try { await releaseBookingHold(heldBookingId) } catch { /* Expired holds are already released server-side. */ }
      setBookingId('')
      setBookingVersion(0)
      setHoldExpiresAt(null)
      floatingDemoContextRef.current.bookingId = ''
      floatingDemoContextRef.current.bookingVersion = 0
    }
    const viewByStep = ['agent', 'agent', 'car', 'map', 'schedule', 'schedule', 'ticket', 'ticket']
    const stageByStep = ['idle', 'idle', 'need_address', 'choose_showroom', 'choose_slot', 'choose_slot', 'review', 'review']
    setFloatingDemoStep(targetStep)
    setMessages((current) => current.filter((message) => {
      const isLaterDemoMessage = message.floatingDemoStep && message.floatingDemoStep > targetStep
      const isLegacySuccessMessage = floatingDemoContextRef.current.isSimulated && (
        message.type === 'next_steps'
        || message.text === BOOKING_PREPARATION_GREETING
        || (message.emphasis && String(message.text || '').includes('ViVi và showroom đều đã nhận được lịch đặt'))
      )
      return !isLaterDemoMessage && !isLegacySuccessMessage
    }))
    setStage(stageByStep[targetStep])
    setActiveView(viewByStep[targetStep])
    setFloatingDemoStatus(`Đã quay lại chặng ${targetStep || 1}.`)
  }

  const handleStartDemoFromModal = () => {
    if (isMobileBookingViewport) return
    setRecipient('self')
    setFloatingDemoEnabled(true)
    setFloatingDemoCollapsed(false)
    window.setTimeout(() => {
      autoPlayFloatingDemo()
    }, 300)
  }

  const handleRestartRealSessionAfterDemo = () => {
    setDemoCompletedModalOpen(false)
    resetFloatingDemo()
    setRecipient('')
    setStage('idle')
    setActiveView('agent')
  }

  const resetFloatingDemo = async () => {
    const hasStartedDemo = floatingDemoStep > 0 || floatingDemoRunning || floatingDemoBusy || Boolean(floatingDemoContextRef.current.car)
    floatingDemoRunRef.current += 1
    floatingDemoPausedRef.current = false
    floatingDemoPauseWaitersRef.current.splice(0).forEach((resolve) => resolve())
    setFloatingDemoRunning(false)
    setFloatingDemoPaused(false)
    setFloatingDemoBusy(true)
    setAgentTyping(false)
    setDraft('')
    const heldBookingId = bookingId || floatingDemoContextRef.current.bookingId
    try {
      if (heldBookingId && !bookingCode && !floatingDemoContextRef.current.isSimulated) await releaseBookingHold(heldBookingId)
    } catch {
      // Backend cleanup may already have released an expired hold; reset stays usable.
    } finally {
      timersRef.current.forEach((timer) => window.clearTimeout(timer))
      timersRef.current = []
      holdActionIdsRef.current.clear()
      confirmActionIdsRef.current.clear()
      floatingDemoContextRef.current = {}
      if (!hasStartedDemo) {
        setFloatingDemoStep(0)
        setFloatingDemoLogs([])
        setFloatingDemoStatus('')
        setFloatingDemoCollapsed(true)
        setFloatingDemoBusy(false)
        return
      }
      window.sessionStorage.removeItem(BOOKING_UI_STATE_KEY)
      resetBookingConversation()
      setResumePending(false)
      setRecipient('')
      setSelectedCarId('')
      setNearbyShowrooms([])
      setShowroomId('')
      setSlots([])
      setPendingSlot(null)
      setSelectedSlot(null)
      setBookingId('')
      setBookingVersion(0)
      setHoldExpiresAt(null)
      setTimeLeft('')
      setBookingCode('')
      setBookingAdvisor(null)
      setPerson({ ...DEMO_PERSONA, bookingName: '', phone: '', email: '', hasLicense: false, marketingConsent: true })
      setMessages([])
      setStage('idle')
      setActiveView('agent')
      setFloatingDemoStep(0)
      setFloatingDemoLogs([])
      setFloatingDemoStatus('Đã sẵn sàng cho lượt demo mới')
      setFloatingDemoCollapsed(true)
      setFloatingDemoBusy(false)
    }
  }

  const toggleFloatingDemo = () => {
    if (isMobileBookingViewport) {
      setFloatingDemoCollapsed(true)
      return
    }
    setFloatingDemoCollapsed((value) => !value)
  }

  // Real booking and lookup flows must take back control immediately. This is
  // intentionally lighter than Reset: it cancels the demo run without wiping
  // the new conversation the visitor has just chosen to start.
  const dismissFloatingDemoForRealFlow = useCallback(() => {
    floatingDemoRunRef.current += 1
    floatingDemoPausedRef.current = false
    floatingDemoPauseWaitersRef.current.splice(0).forEach((resolve) => resolve())
    floatingDemoContextRef.current = {}
    setFloatingDemoEnabled(false)
    setFloatingDemoRunning(false)
    setFloatingDemoPaused(false)
    setFloatingDemoBusy(false)
    setFloatingDemoStep(0)
    setFloatingDemoLogs([])
    setFloatingDemoStatus('')
    setFloatingDemoCollapsed(true)
    setAgentTyping(false)
    setDraft('')
  }, [])

  // A demo that began on desktop remains controllable after a resize. New
  // mobile sessions still never expose a Demo entry point.
  useEffect(() => {
    if (isMobileBookingViewport && floatingDemoEnabled) setFloatingDemoCollapsed(true)
  }, [isMobileBookingViewport, floatingDemoEnabled])

  // Đặt lịch xong thì thanh tab chỉ còn ĐÚNG 1 nút "Phiếu lịch".
  // Ba tab kia (Đổi mẫu xe, Showroom, Lịch trống) là công cụ của lúc đang đặt; giữ lại sau khi
  // đã có mã lịch thì thanh vừa dài vừa mời khách bấm vào những thứ không còn tác dụng, trong
  // khi renderWorkspace() ở stage 'success' luôn trả về phiếu lịch bất kể activeView là gì.
  // Muốn đổi xe hoặc đổi giờ sau khi đã đặt thì dùng nút "Đổi hoặc huỷ lịch" ở khung chat.
  const viewOptions = workspaceModel.kind === 'new_booking' ? (
    stage === 'success'
      ? (selectedCar && selectedShowroom && selectedSlot
        ? [{ id: 'ticket', label: 'Phiếu lịch', icon: CheckCircle }]
        : [])
      : [
        ...(selectedCar ? [
          { id: 'car', label: 'Đổi mẫu xe', icon: CarProfile },
          ...(nearbyShowrooms.length ? [{ id: 'map', label: 'Showroom', icon: MapPin }] : []),
          ...(selectedShowroom ? [{ id: 'schedule', label: 'Lịch trống', icon: CalendarBlank }] : []),
          ...(stage === 'review' ? [{ id: 'ticket', label: 'Phiếu lịch', icon: CheckCircle }] : []),
        ] : []),
      ]
  ) : accessProfile ? [{ id: 'bookings', label: 'Lịch đã đặt', icon: CalendarBlank }] : []

  /**
   * Tiêu đề của bảng bên trái, hiển thị NGAY TRONG thanh công cụ.
   *
   * Trước đây mỗi bảng tự in tiêu đề trong thân mình, mà thanh công cụ lại `position: absolute`
   * nổi phía trên — nên tiêu đề luôn nằm THẤP hơn hàng nút một khoảng, trông như hai tầng rời
   * nhau. Đưa vào chung một hàng flex là cách duy nhất canh chuẩn được, vì bề rộng thanh công
   * cụ đổi theo số nút (2, 3 hay 4 nút tuỳ bước).
   */
  const workspaceTitle = (() => {
    if (rescheduleState?.step === 'showroom') return 'Chọn showroom khác'
    if (rescheduleState?.car && rescheduleState?.showroom) {
      return `${rescheduleState.car.name} tại ${rescheduleState.showroom.name}`
    }
    if (activeView === 'bookings' && accessProfile) return 'Chọn lịch cần thao tác'
    return ''
  })()

  const highlightedDates = serverHighlightedDates || []
  const mobileWorkspaceLabel = activeView === 'map'
    ? 'Chọn showroom'
    : activeView === 'schedule'
      ? 'Chọn lịch'
      : activeView === 'ticket'
        ? 'Phiếu lịch'
        : activeView === 'bookings'
          ? 'Lịch đã đặt'
          : 'Mẫu xe'

  const renderWorkspace = () => {
    if (activeView === 'bookings' && accessProfile) {
      return (
        <section className="booking-history">
          <div className="booking-history__list">
            {accessibleBookings.map((booking) => {
              const expanded = expandedBookingId === booking.id
              const details = booking.id === accessProfile.bookingId ? accessProfile : null
              const bookingCodeLabel = booking.booking_code || 'Lịch lái thử'
              const displayTime = booking.display_time || (booking.start_at
                ? new Intl.DateTimeFormat('vi-VN', {
                  weekday: 'long',
                  day: '2-digit',
                  month: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                }).format(new Date(booking.start_at))
                : 'Lịch lái thử')

              return (
                <div key={booking.id} className={expanded ? 'is-active is-expanded' : ''}>
                  <button
                    type="button"
                    onClick={() => {
                      setExpandedBookingId(expanded ? '' : booking.id)
                      if (!expanded) selectAccessibleBooking(booking)
                    }}
                  >
                    <strong>{bookingCodeLabel}</strong>
                    <small>{displayTime}</small>
                  </button>

                  {expanded && details && (
                    <div className="booking-history__details">
                      <p><span>Mẫu xe</span>{details.vehicleName}</p>
                      <p><span>Showroom</span>{details.showroomName}<small>{details.showroomAddress}</small></p>
                      <p><span>Thời gian hiện tại</span>{details.slotTime} · {details.slotDate}</p>
                      {rescheduleState?.step === 'pending' && rescheduleState.slot && (() => {
                        const startsAt = new Date(rescheduleState.slot.start_at || rescheduleState.slot.startAt)
                        const timeStr = startsAt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false })
                        const dateStr = new Intl.DateTimeFormat('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit' }).format(startsAt)
                        return (
                          <div className="booking-history__hold">
                            <p style={{ display: 'flex', justifyContent: 'space-between', margin: 0 }}>
                              <span style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>Khung giờ mới đang giữ tạm</span>
                              <small style={{ fontSize: '0.78rem', fontWeight: 600 }}>Còn lại {Math.floor(rescheduleSecondsLeft / 60)}:{String(rescheduleSecondsLeft % 60).padStart(2, '0')}</small>
                            </p>
                            <strong style={{ fontSize: '0.94rem', fontWeight: 600 }}>{timeStr} · {dateStr}</strong>
                          </div>
                        )
                      })()}
                      <p><span>Tư vấn viên</span>{details.advisorName}<small>{details.advisorPhone || 'Chưa có số điện thoại'}</small></p>
                      <div className="booking-history__actions">
                        <span className="booking-history__actions-main">
                          <button
                            type="button"
                            className="booking-history__action"
                            onClick={() => {
                              if (rescheduleState?.car && rescheduleState?.showroom && rescheduleState?.slots) {
                                setRescheduleState((current) => ({ ...current, step: 'schedule' }))
                                dispatchInteraction({ type: InteractionEvent.RESCHEDULE_SLOT })
                              } else {
                                beginAccessibleReschedule(booking)
                              }
                            }}
                            aria-label={`Đổi ngày giờ lịch ${bookingCodeLabel}`}
                          >
                            <PencilSimple size={13} weight="bold" aria-hidden="true" />
                            <span>{rescheduleState?.step === 'pending' ? 'Đổi sang ngày giờ khác' : 'Đổi giờ'}</span>
                          </button>

                          {details.allowedActions?.includes('cancel') && (
                            <button
                              type="button"
                              className="booking-history__action booking-history__action--danger"
                              onClick={() => beginAccessibleCancellation(booking)}
                              aria-label={`Huỷ lịch ${bookingCodeLabel}`}
                            >
                              <Prohibit size={13} weight="bold" aria-hidden="true" />
                              <span>Huỷ lịch</span>
                            </button>
                          )}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      )
    }
    if (rescheduleState?.step === 'showroom') return <section className="studio-schedule"><div className="reschedule-left-grid">{rescheduleState.showrooms.map((showroom) => <button type="button" key={showroom.id} onClick={() => loadRescheduleSlots(rescheduleState.car, showroom)}><strong>{showroom.name}</strong><small>{showroom.address}</small></button>)}</div></section>
    if (rescheduleState?.step === 'schedule') return <SchedulePanel compact onBack={exitReschedule} car={rescheduleState.car} showroom={rescheduleState.showroom} slots={groupSlots(rescheduleState.slots)} pendingSlot={null} highlightedDates={highlightedDates} onPick={(picked) => holdReschedule(rescheduleState.slots.find((slot) => slot.id === picked.slotId))} />
    if (rescheduleState?.step === 'pending') return <SchedulePanel compact onBack={exitReschedule} car={rescheduleState.car} showroom={rescheduleState.showroom} slots={groupSlots(rescheduleState.slots)} pendingSlot={{ slotId: rescheduleState.slot.id }} highlightedDates={highlightedDates} onPick={(picked) => holdReschedule(rescheduleState.slots.find((slot) => slot.id === picked.slotId))} />
    if (rescheduleState?.step === 'confirm') return <section className="studio-schedule"><div className="studio-schedule__heading"><span>Đang chờ xác nhận</span><h2>Xác nhận lịch ở cửa sổ bên phải</h2></div></section>
    if (!selectedCar) return null
    if (stage === 'success' && selectedShowroom && selectedSlot) {
      return (
        <div className="booking-success-documents">
          <VehiclePanel car={selectedCar} />
          <BookingTicket car={selectedCar} showroom={selectedShowroom} slot={selectedSlot} person={person} recipient={recipient} bookingCode={bookingCode} advisor={bookingAdvisor} compact />
        </div>
      )
    }
    if (activeView === 'map') return <BookingShowroomMap car={selectedCar} showrooms={nearbyShowrooms} selectedId={showroomId} onSelect={setShowroomId} onConfirm={chooseShowroom} userLocation={userLocation} searchedLocation={searchedLocation} disabled={floatingDemoMode} />
    if (activeView === 'schedule' && selectedShowroom) return <SchedulePanel car={selectedCar} showroom={selectedShowroom} slots={slots} pendingSlot={pendingSlot} highlightedDates={highlightedDates} onPick={chooseSlot} disabled={floatingDemoMode || agentTyping || isSending || submitting || calendarState.loading} calendarLoading={calendarState.loading} calendarError={calendarState.error} />
    if (activeView === 'ticket' && selectedShowroom && selectedSlot) return <BookingTicket car={selectedCar} showroom={selectedShowroom} slot={selectedSlot} person={person} recipient={recipient} bookingCode={bookingCode} advisor={bookingAdvisor} />
    return <VehiclePanel car={selectedCar} />
  }

  const showVehicleChoices = allowedActions.includes('choose_vehicle') && !accessProfile && interaction.mode !== BookingMode.MANAGE_BOOKING
  const latestMessage = messages[messages.length - 1]
  const bookingWorkflowOwnsComposer = composerMode !== 'chat'
    || showVehicleChoices
    || ['need_address', 'need_ward', 'choose_showroom', 'choose_slot', 'collect_info', 'review'].includes(stage)
  const visibleFollowUps = !agentTyping && !isSending && !bookingWorkflowOwnsComposer
    && latestMessage?.role === 'assistant'
    && String(latestMessage.id) === completedAssistantMessageId
    && Array.isArray(latestMessage.followUps)
    ? latestMessage.followUps
    : []
  const showFloatingDemo = floatingDemoEnabled
    && (!isMobileBookingViewport || floatingDemoMode)
    && Boolean(recipient)
    && !resumePending
    && !demoCompletedModalOpen
    && !isDriverChat
    && !successCinematic
    && !confirmSlotOpen
    && !switcherOpen
    && !accessFlow
    && !rescheduleState

  if (bookingStatus === 'unavailable') {
    return (
      <main id="main-content" className="booking-unavailable">
        <Brand />
        <div>
          <span>Dịch vụ đặt lịch</span>
          <h1>Backend hiện không khả dụng.</h1>
          <p>Dữ liệu xe, showroom, lịch trống và thao tác giữ chỗ đều cần kết nối backend.</p>
          <button type="button" onClick={retry}>Thử kết nối lại</button>
          <Link to="/">Quay về trang chủ</Link>
        </div>
      </main>
    )
  }

  return (
    <main id="main-content" className={`agent-booking-page ${workspaceVisible ? 'has-workspace' : 'is-agent-only'} ${showFloatingDemo ? 'has-floating-demo' : ''} ${stage === 'success' ? 'is-success' : ''} ${successCinematic ? 'is-cinematic' : ''}`}>
      <BookingHeader />

      {showFloatingDemo && (
        <FloatingDemoBar
          step={floatingDemoStep}
          running={floatingDemoRunning}
          paused={floatingDemoPaused}
          busy={floatingDemoBusy}
          collapsed={floatingDemoCollapsed}
          logs={floatingDemoLogs}
          onAutoPlay={autoPlayFloatingDemo}
          onPause={toggleFloatingDemoPause}
          onNext={advanceFloatingDemo}
          onBack={rewindFloatingDemo}
          onExit={resetFloatingDemo}
          onToggle={toggleFloatingDemo}
        />
      )}

      {workspaceModel.visible && hasWorkspaceContent && workspaceHidden && (
        <button
          type="button"
          onClick={() => setWorkspaceHidden(false)}
          className="workspace-restore-button"
          style={{
            position: 'fixed',
            left: '37px',
            top: '117px',
            zIndex: 99,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '7px',
            height: '38px',
            padding: '0 13px',
            borderRadius: '11px',
            background: '#ffffff',
            color: '#4a4d52',
            border: '1px solid rgba(0,0,0,0.05)',
            cursor: 'pointer',
            fontWeight: '620',
            fontSize: '0.73rem',
            boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
            transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor = '#20252b'
            e.currentTarget.style.color = '#ffffff'
            e.currentTarget.style.borderColor = '#20252b'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = '#ffffff'
            e.currentTarget.style.color = '#4a4d52'
            e.currentTarget.style.borderColor = 'rgba(0,0,0,0.05)'
          }}
        >
          <ArrowRight size={16} weight="bold" />
          <span style={{ fontSize: '0.73rem', fontWeight: '700', letterSpacing: '-0.01em' }}>Hiện bảng</span>
        </button>
      )}

      {!recipient && !resumePending && !demoCompletedModalOpen && (
        <RecipientModal
          onBack={leaveRecipientModal}
          onSelect={beginConversation}
          onLookup={() => {
            // Chọn 'self' chỉ để đóng modal (modal hiện khi chưa có recipient); người dùng
            // đi nhánh tra cứu nên câu "đặt cho ai" chưa cần trả lời lúc này.
            dismissFloatingDemoForRealFlow()
            clearBookingReturnContext()
            setRecipient('self')
            startLookup({ addUserMessage: false })
          }}
          onDemo={isMobileBookingViewport ? undefined : handleStartDemoFromModal}
        />
      )}
      {demoCompletedModalOpen && (
        <DemoCompletionModal
          onRestartRealSession={handleRestartRealSessionAfterDemo}
          onClose={() => setDemoCompletedModalOpen(false)}
        />
      )}
      {resumePending && (
        <ResumeModal
          onBack={leaveResumeModal}
          onContinue={resumeConversation}
          onRestart={restartConversation}
        />
      )}
      {successCinematic && selectedCar && (
        <BookingSuccessCinematic car={selectedCar} onComplete={completeBookingSuccess} />
      )}

      {/* Đặt lịch xong KHÔNG đổi sang một bố cục khác nữa.
          Trước đây stage 'success' render `booking-success-layout` riêng: panel trái là phiếu,
          panel phải là một trang tĩnh — đoạn hội thoại với ViVi biến mất, người dùng đang nói
          chuyện dở thì đột nhiên mất người đối thoại.
          Nay dùng đúng bố cục 2 màn quen thuộc: TRÁI giữ phiếu lịch (tab "Phiếu lịch" đã có
          sẵn trong viewOptions cho stage success), PHẢI vẫn là khung chat để ViVi tiếp tục
          hướng dẫn và trả lời. Xem completeBookingSuccess() và successActions bên dưới. */}
      <div
        className={`booking-studio ${workspaceVisible ? 'booking-studio--split' : 'booking-studio--agent'}`}
        data-mobile-surface={mobileSurface}
      >
          {workspaceVisible && (
            <section id="booking-mobile-workspace" className="booking-workspace" aria-label="Thông tin lịch lái thử">
              {/* Hàng công cụ = viên pill chứa các nút + tiêu đề đứng cạnh, cùng một trục ngang. */}
              <div className="workspace-toolbar">
              <div className="workspace-switcher" role="tablist" aria-label="Nội dung hỗ trợ đặt lịch">
                {/* Đang ở giữa luồng đổi giờ thì lối lùi phải nằm NGAY trên thanh công cụ,
                    cùng hàng với "Lịch đã đặt" và "Ẩn bảng", theo thứ tự trái→phải. Đặt trong
                    thân bảng như bản trước thì người dùng phải cuộn mới thấy. */}
                {rescheduleState && (
                  <button
                    type="button"
                    className="workspace-switcher__back"
                    onClick={exitReschedule}
                  >
                    <CaretLeft size={15} weight="bold" /> Chọn lịch khác
                  </button>
                )}
                {viewOptions.map(({ id, label, icon: Icon }) => {
                  const active = activeView === id
                  // Tab "Mẫu xe" khi đang mở sẽ đóng vai trò nút đổi xe: bấm lần nữa mở bảng chọn.
                  const isCarTab = id === 'car'
                  return (
                    <button
                      type="button"
                      role="tab"
                      key={id}
                      aria-selected={active}
                      aria-haspopup={isCarTab ? 'dialog' : undefined}
                      title={floatingDemoMode ? 'Đang trong chế độ demo' : isCarTab ? 'Bấm lần nữa để đổi mẫu xe' : undefined}
                      className={`${active ? 'is-active' : ''} ${isCarTab ? 'is-car-tab' : ''}`.trim()}
                      disabled={floatingDemoMode}
                      style={floatingDemoMode ? { cursor: 'default' } : undefined}
                      onClick={() => {
                        if (floatingDemoMode) return
                        if (isCarTab && active) setSwitcherOpen(true)
                        else setActiveView(id)
                      }}
                    >
                      <Icon size={16} weight="light" /> {label}
                      {isCarTab && <CaretDown size={11} weight="bold" />}
                    </button>
                  )
                })}
                <button
                  type="button"
                  title="Ẩn bảng hỗ trợ"
                  className="workspace-switcher__close"
                  onClick={() => setWorkspaceHidden(true)}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: '#92959a',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '0.78rem',
                    padding: '4px 8px',
                    borderRadius: '8px',
                    transition: 'color 0.2s',
                  }}
                  onMouseOver={(e) => e.currentTarget.style.color = '#ff4d4f'}
                  onMouseOut={(e) => e.currentTarget.style.color = '#92959a'}
                >
                  <X size={14} weight="bold" /> Ẩn bảng
                </button>
              </div>
              {workspaceTitle && <h2 className="workspace-toolbar__title">{workspaceTitle}</h2>}
              </div>
              <div className={`booking-workspace__content${activeView === 'map' && !rescheduleState ? ' booking-workspace__content--map' : ''}`} key={activeView}>{renderWorkspace()}</div>
            </section>
          )}

          <section
            id="booking-mobile-assistant"
            className="vivi-studio"
            aria-label="Trợ lý ViVi"
            onTouchMove={markMessageScrollIntent}
            onWheel={markMessageScrollIntent}
          >
            <div className="vivi-studio__head">
              <ViViAvatar />
              <div><strong>ViVi</strong><small><span /> {isDriverChat ? 'Hỗ trợ chuẩn bị lái thử' : 'Trợ lý đặt lịch lái thử'}</small></div>
              <div className="vivi-studio__head-actions">
                <Link className="vivi-studio__home-link" to="/" aria-label="Quay về trang chủ">
                  <ArrowLeft size={16} weight="bold" aria-hidden="true" />
                  <span>Trang chủ</span>
                </Link>
                {!isDriverChat && !floatingDemoEnabled && (
                  <button
                    type="button"
                    className="vivi-studio__menu-button"
                    onClick={() => !floatingDemoMode && setActionMenuOpen(true)}
                    disabled={floatingDemoMode}
                    aria-haspopup="dialog"
                    aria-expanded={actionMenuOpen}
                    aria-label="Mở menu thao tác lịch"
                    style={floatingDemoMode ? { opacity: 0.38, cursor: 'not-allowed', pointerEvents: 'none' } : undefined}
                    title={floatingDemoMode ? 'Menu tạm khóa trong chế độ demo' : 'Menu'}
                  >
                    <List size={21} weight="bold" aria-hidden="true" />
                  </button>
                )}
              </div>
            </div>

            <div
              className="vivi-studio__messages"
              ref={messagesRef}
              aria-live="polite"
            >
              {resumePending ? (
                <div className="vivi-studio__empty"><ViViAvatar /><p>Bạn đang có một phiên đặt lịch đang dở.</p></div>
              ) : messages.length ? messages.map((message, index) => message.type === 'next_steps' ? (
                <div key={message.id} className="vivi-message vivi-message--assistant vivi-message--card">
                  <ViViAvatar compact />
                  <BookingNextSteps slot={selectedSlot} person={person} recipient={recipient} />
                </div>
              ) : (
                <AgentMessage
                  key={message.id}
                  message={message}
                  isLatest={index === messages.length - 1}
                  onTypingComplete={revealCompletedAssistantMessage}
                />
              )) : (
                <div className="vivi-studio__empty"><ViViAvatar /><p>Chọn người lái thử để ViVi bắt đầu.</p></div>
              )}
              {agentTyping && (
                <div className="vivi-message vivi-message--assistant">
                  <ViViAvatar compact />
                  <ViviStatusTyping />
                </div>
              )}
            </div>

            <div className="vivi-studio__composer" ref={composerRef}>
              {backendError && <p className="booking-api-error" role="alert">{backendError}</p>}
              {resumePending ? (
                null
              ) : (['access_request', 'access_verify', 'booking_edit'].includes(composerMode) || accessProfile) && accessFlow?.phase !== 'confirm_cancel' ? (
                <BookingAccessPanel
                  phase={accessFlow?.phase || 'edit'}
                  value={accessValue}
                  onChange={changeAccessValue}
                  onRequest={requestAccessOtp}
                  onVerify={verifyAccessOtp}
                  onResend={requestAccessOtp}
                  onCancelAccess={cancelAccessOtp}
                  onCloseDetails={closeBookingDetails}
                  secondsLeft={accessSecondsLeft}
                  resendLeft={resendSecondsLeft}
                  error={accessError}
                  busy={accessBusy}
                  profile={accessProfile}
                  canUpdate={allowedActions.includes('update_details')}
                  onProfileChange={changeAccessProfile}
                  onProfileSave={saveAccessProfile}
                  onBookingCancel={confirmCancellation}
                />
              ) : (
                <>
              {showVehicleChoices && (
                <BookingUpsell
                  cars={upsellCars}
                  onChoose={chooseCar}
                  onBrowseAll={() => setSwitcherOpen(true)}
                  totalCount={cars.length}
                  headline={upsell.headline}
                  note={upsell.note}
                />
              )}

              <ContextualChoices
                stage={stage}
                allowedActions={allowedActions}
                car={selectedCar}
                locationSuggestions={locationSuggestions}
                showrooms={nearbyShowrooms}
                slots={slots}
                pendingSlot={pendingSlot}
                highlightedDates={highlightedDates}
                disabled={floatingDemoMode}
                onResolveArea={resolveSuggestedArea}
                onShowroom={chooseShowroom}
                onSlot={chooseSlot}
              />

              {visibleFollowUps.length > 0 && (
                <div className="post-booking-follow-ups" aria-label="Gợi ý câu hỏi tiếp theo">
                  {visibleFollowUps.map((followUp, index) => (
                    <button
                      key={`${followUp.text}-${index}`}
                      type="button"
                      disabled={composerDisabled}
                      onClick={() => handlePrompt({ preventDefault: () => {} }, followUp.text)}
                    >
                      {followUp.text}
                      <ArrowRight size={15} weight="bold" aria-hidden="true" />
                    </button>
                  ))}
                </div>
              )}

              {/* Hàng nút nhanh ngay trên ô nhập.
                  Các thao tác quản lý lịch và hậu đặt lịch đã được gom vào menu ở header:
                  không lặp lại chúng trong vùng composer để giữ không gian trò chuyện.
                  - "Đổi mẫu xe khác"      → trùng tab "Đổi mẫu xe" ở panel trái, bấm vào cũng
                    mở đúng bảng chọn xe đó.
                  Đừng thêm lại: mỗi hành động chỉ có một điểm truy cập rõ ràng. */}
              {(allowedActions.some((action) => (
                action === 'choose_vehicle' ? !showVehicleChoices : ['use_geolocation', 'view_vehicle'].includes(action)
              )) || stage === 'need_address' || stage === 'choose_showroom') && (
                <div className="vivi-capabilities">
                  {(stage === 'need_address' || stage === 'choose_showroom' || allowedActions.includes('use_geolocation')) && (
                    <button className="vivi-capabilities__location" type="button" onClick={requestUserLocation} disabled={floatingDemoMode}>
                      <NavigationArrow size={14} weight="light" style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                      Định vị hiện tại
                    </button>
                  )}
                  {allowedActions.includes('choose_vehicle') && !showVehicleChoices && (
                    <button type="button" onClick={() => setSwitcherOpen(true)} disabled={floatingDemoMode} aria-haspopup="dialog">
                      <CarProfile size={14} weight="light" style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                      Xem tất cả {cars.length} mẫu
                    </button>
                  )}
                  {allowedActions.includes('view_vehicle') && (
                    <button type="button" onClick={() => setSwitcherOpen(true)} disabled={floatingDemoMode} aria-haspopup="dialog">
                      <CarProfile size={14} weight="light" style={{ marginRight: '4px', verticalAlign: 'middle' }} />
                      Xem mẫu xe khác
                    </button>
                  )}
                </div>
              )}

              {timeLeft && (stage === 'collect_info' || stage === 'review') && (
                /* Style nằm ở styles/12-booking-modals.css, KHÔNG đặt inline nữa:
                   bản cũ gán cứng màu cam #e25c00 và font monospace, cả hai đều nằm ngoài
                   hệ màu và bộ chữ của web. */
                <div className="vivi-hold-timer">
                  <Clock size={14} weight="light" aria-hidden="true" />
                  <span>Khung giờ đang được ViVi giữ trong</span>
                  <strong>{timeLeft}</strong>
                </div>
              )}

              {stage === 'collect_info' ? (
                <CustomerForm
                  recipient={recipient}
                  value={person}
                  errors={formErrors}
                  disabled={floatingDemoMode || submitting}
                  busy={submitting}
                  onChange={changePerson}
                  onSubmit={submitPerson}
                  onBack={async () => {
                    const currentBookingId = bookingId
                    const canceledSlotId = pendingSlot?.slotId || selectedSlot?.slotId
                    if (currentBookingId) {
                      try {
                        await releaseBookingHold(currentBookingId)
                      } catch {
                        // ignore error
                      }
                    }
                    if (canceledSlotId) {
                      setSlots((prevSlots) =>
                        prevSlots.map((day) => ({
                          ...day,
                          times: day.times.map((t) =>
                            t.slotId === canceledSlotId
                              ? { ...t, isAvailable: true, unavailableLabel: '' }
                              : t
                          ),
                        }))
                      )
                    }
                    holdActionIdsRef.current.clear()
                    setBookingId('')
                    setPendingSlot(null)
                    setSelectedSlot(null)
                    setStage('choose_slot')
                    showMobileWorkspace('schedule')
                    reply('Đã hủy giữ chỗ và giải phóng khung giờ. Bạn có thể chọn lại ngay khung giờ này hoặc chọn giờ khác nhé.')
                  }}
                />
              ) : stage === 'review' ? (
                <>
                  <div className="vivi-inline-otp">
                    <div className="vivi-inline-otp__header">
                      <span>Xác thực OTP người đặt</span>
                      <small>Mã 6 chữ số vừa gửi tới <strong>{person.email}</strong></small>
                    </div>

                    <div className="vivi-inline-otp__boxes">
                      {inlineOtpDigits.map((digit, index) => (
                        <input
                          key={index}
                          id={`review-otp-${index}`}
                          aria-label={`Mã OTP số ${index + 1}`}
                          className="vivi-inline-otp__box"
                          inputMode="numeric"
                          maxLength={1}
                          value={digit}
                          disabled={submitting}
                          onKeyDown={(e) => handleInlineOtpKeyDown(index, e)}
                          onPaste={handleInlineOtpPaste}
                          onChange={(e) => handleInlineOtpDigit(index, e.target.value)}
                        />
                      ))}
                    </div>

                    <div className="vivi-inline-otp__resend-wrapper">
                      <button
                        type="button"
                        className="vivi-inline-otp__resend-btn"
                        disabled={resendSecondsLeft > 0 || submitting}
                        onClick={() => {
                          setInlineOtpDigits(['', '', '', '', '', ''])
                          setInlineOtpError('')
                          requestInlineOtp(person.email)
                        }}
                      >
                        {resendSecondsLeft > 0 ? `Gửi lại OTP sau ${resendSecondsLeft}s` : 'Gửi lại OTP'}
                      </button>
                    </div>

                    {(inlineOtpError || inlineOtpMock) && (
                      <div className="vivi-inline-otp__error" role="alert">
                        {inlineOtpError ? inlineOtpError : `Mã mock: ${inlineOtpMock}`}
                      </div>
                    )}
                  </div>

                  <div className="vivi-review-actions">
                    <button
                      type="button"
                      onClick={confirmFinalBooking}
                      disabled={!isInlineOtpComplete || submitting}
                      className={isInlineOtpComplete ? 'is-enabled-confirm' : 'is-disabled-confirm'}
                    >
                      {submitting ? 'Đang kiểm tra & chốt lịch...' : 'Xác nhận đặt lịch'} <Check size={16} weight="light" />
                    </button>
                    <button
                      type="button"
                      onClick={() => { setStage('collect_info'); setActiveView('schedule') }}
                    >
                      Chỉnh lại thông tin
                    </button>
                  </div>
                </>
              ) : (
                <form className="vivi-prompt" onSubmit={handlePrompt} aria-busy={composerDisabled}>
                {/* Ô nhập KHÔNG disable trong lúc ViVi trả lời. Phần tử disabled không giữ
                    được tiêu điểm — trình duyệt blur nó ngay, và khi bật lại thì tiêu điểm
                    KHÔNG tự quay về, nên sau mỗi câu trả lời người dùng phải bấm lại vào ô.
                    Chặn gửi trùng đã có đủ ba lớp: guard sendingRef trong handlePrompt, nút
                    submit disabled, và nhánh Enter bên dưới. Giữ ô mở còn cho phép gõ trước
                    câu tiếp theo trong lúc chờ. Chỉ chế độ demo mới thật sự khoá ô nhập.
                    Trạng thái bận vẫn thấy được qua aria-busy (nền ô đổi màu, 11-booking-upsell.css). */}
                  <label htmlFor="vivi-booking-prompt">Nhắn cho ViVi</label>
                  <div>
                    <textarea id="vivi-booking-prompt" rows="2" value={draft} maxLength={CHAT_MESSAGE_MAX_LENGTH} disabled={floatingDemoMode} onChange={(event) => setDraft(event.target.value)} placeholder={floatingDemoMode ? 'Demo đang mở — dùng điều khiển demo để tiếp tục' : composerDisabled ? 'ViVi đang thực hiện tác vụ cho bạn' : isDriverChat ? 'Chia sẻ điều bạn muốn chuẩn bị cho buổi lái thử…' : stage === 'need_address' || stage === 'need_ward' ? 'Ví dụ: Phường Bến Nghé, TP. Hồ Chí Minh' : 'Nhập mẫu xe, địa chỉ, showroom hoặc thời gian…'} onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        if (!composerDisabled) event.currentTarget.form?.requestSubmit()
                      }
                    }} />
                    <button type="submit" aria-label="Gửi tin nhắn" disabled={composerDisabled || !draft.trim()}><PaperPlaneTilt size={18} weight="light" /></button>
                  </div>
                  <small>Enter để gửi · Shift + Enter để xuống dòng · {draft.length.toLocaleString('vi-VN')}/{CHAT_MESSAGE_MAX_LENGTH.toLocaleString('vi-VN')}</small>
                </form>
              )}
            </>
          )}
            </div>
          </section>
        </div>

      {workspaceVisible && (
        <nav className="booking-mobile-tabs" role="tablist" aria-label="Chuyển nội dung đặt lịch">
          <button
            type="button"
            role="tab"
            aria-selected={mobileSurface === 'assistant'}
            aria-controls="booking-mobile-assistant"
            onClick={() => setMobileSurface('assistant')}
          >
            <ChatCircleDots size={19} weight="light" aria-hidden="true" />
            <span>ViVi</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mobileSurface === 'workspace'}
            aria-controls="booking-mobile-workspace"
            onClick={() => setMobileSurface('workspace')}
          >
            <SquaresFour size={19} weight="light" aria-hidden="true" />
            <span>{mobileWorkspaceLabel}</span>
          </button>
        </nav>
      )}

      <BookingActionMenu
        open={actionMenuOpen}
        onClose={() => setActionMenuOpen(false)}
        hasConfirmedBooking={Boolean(bookingCode)}
        onAddToCalendar={addBookingToCalendar}
        onManageBooking={() => startLookup({ addUserMessage: false })}
        onBookAnother={bookAnotherVehicle}
        onLookup={startLookup}
      />

      {switcherOpen && (
        <VehicleSwitcher
          cars={cars}
          currentId={selectedCarId}
          onSelect={pickCarFromSwitcher}
          onClose={() => setSwitcherOpen(false)}
        />
      )}

      {confirmSlotOpen && selectedCar && selectedShowroom && pendingSlot && (
        <div ref={slotDialogRef} className="slot-confirm-modal" role="dialog" aria-modal="true" aria-labelledby="slot-confirm-title" tabIndex={-1}>
          <div>
            <button type="button" onClick={() => setConfirmSlotOpen(false)} aria-label="Đóng"><X size={17} weight="light" /></button>
            <div className="slot-confirm-summary" aria-hidden="true">
              <span>{pendingSlot.dateLabel}</span>
              <strong>{pendingSlot.time}</strong>
            </div>
            <p>Xác nhận khung giờ</p>
            <h2 id="slot-confirm-title">Bạn sẽ lái thử {selectedCar.name}</h2>
            <dl>
              <div><dt>Showroom</dt><dd>{selectedShowroom.name}</dd></div>
              <div><dt>Thời gian</dt><dd>{pendingSlot.time} · {pendingSlot.dateLabel}</dd></div>
              <div><dt>Mẫu xe</dt><dd>{selectedCar.name} đã được giữ cho slot này</dd></div>
            </dl>
            <div className="slot-confirm-actions"><button type="button" onClick={confirmSlot} disabled={submitting}>{submitting ? 'Đang giữ khung giờ...' : 'Xác nhận khung giờ'}</button><button type="button" disabled={submitting} onClick={() => setConfirmSlotOpen(false)}>Hủy xác nhận</button></div>
          </div>
        </div>
      )}
      {rescheduleState?.step === 'confirm' && <RescheduleConfirmModal state={rescheduleState} secondsLeft={rescheduleSecondsLeft} onConfirm={confirmReschedule} onBack={() => setRescheduleState((current) => ({ ...current, step: 'pending' }))} busy={accessBusy} />}
      {accessFlow?.phase === 'confirm_cancel' && accessProfile && (
        <CancellationConfirmModal
          profile={accessProfile}
          car={cars.find((car) => car.name === accessProfile.vehicleName) || null}
          onConfirm={confirmCancellation}
          onClose={dismissCancellation}
          busy={accessBusy}
          error={accessError}
        />
      )}
    </main>
  )
}
