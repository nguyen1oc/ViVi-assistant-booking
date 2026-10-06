/**
 * components/booking/BookingSummary.jsx — Bảng chọn khung giờ và Phiếu đặt lịch.
 *
 * ✅ ĐANG DÙNG THẬT: BookingPage.jsx import cả 2 component bên dưới.
 *
 * - SchedulePanel: lịch tuần kiểu Calendar (bước 4). User có thể chuyển tuần; từng ô cho
 *   biết đúng mẫu xe còn trống, đã kín, hoặc showroom chưa mở lịch. Lịch do backend trả về,
 *   frontend chỉ dựng các ngày/ô trống để tạo ngữ cảnh và tuyệt đối không tự tạo slot.
 *
 * - BookingTicket: phiếu đặt lịch, dùng ở HAI nơi với giao diện hơi khác nhau —
 *   màn xem lại trước khi đặt (chưa có bookingCode) và màn thành công (prop compact + có mã lịch).
 *   Gồm ảnh xe, 8 dòng thông tin và dòng xác nhận đã có giấy phép lái xe.
 *
 * Tư vấn viên chỉ hiển thị sau khi backend xác nhận và trả về nhân viên được gán thật.
 *
 * Style tương ứng: .studio-schedule và .studio-ticket trong index.css.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useGSAP } from '@gsap/react'
import gsap from 'gsap'
import { CalendarBlank, CalendarPlus, CaretLeft, CaretRight, CheckCircle, Clock } from '@phosphor-icons/react'
import { VehicleShot } from './VehicleWorkspace'

const WEEKDAY_LABELS = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN']
const DEFAULT_TIMES = ['09:00', '10:30', '14:00', '15:30']

const parseDateValue = (value) => {
  const [year, month, day] = String(value || '').split('-').map(Number)
  return year && month && day ? new Date(year, month - 1, day, 12) : new Date()
}

const dateKey = (date) => [
  date.getFullYear(),
  String(date.getMonth() + 1).padStart(2, '0'),
  String(date.getDate()).padStart(2, '0'),
].join('-')

const addDays = (date, amount) => {
  const next = new Date(date)
  next.setDate(next.getDate() + amount)
  return next
}

const startOfWeek = (date) => {
  const monday = new Date(date)
  const offset = (monday.getDay() + 6) % 7
  monday.setDate(monday.getDate() - offset)
  monday.setHours(12, 0, 0, 0)
  return monday
}

const timeKey = (value) => String(value || '').slice(0, 5)
const timeAsMinutes = (value) => {
  const [hour, minute] = timeKey(value).split(':').map(Number)
  return (hour * 60) + minute
}

/**
 * Bảng chọn khung giờ. Dùng ở hai nơi:
 *   - luồng đặt mới  → đầy đủ như cũ
 *   - luồng ĐỔI GIỜ  → truyền `onBack` và `compact`
 *
 * `compact` lược bớt cho đỡ rối (anh Minh phản ánh 18/08/2026): bỏ câu hướng dẫn, bỏ chú thích
 * màu, và bỏ tên xe lặp trong TỪNG ô. Tên xe đã nằm ở tiêu đề ngay trên, in lại ở 50 ô nữa chỉ
 * làm mắt phải lọc. `onBack` là lối quay về danh sách lịch — trước đây vào màn này là kẹt,
 * không có đường lùi.
 */
export function SchedulePanel({ car, showroom, slots, pendingSlot, highlightedDates = [], onPick, onBack, backLabel = 'Chọn lịch khác', compact = false, disabled = false, calendarLoading = false, calendarError = '' }) {
  const calendarIncomplete = calendarLoading || Boolean(calendarError)
  const root = useRef(null)
  const direction = useRef(0)
  const today = new Date()
  today.setHours(12, 0, 0, 0)
  const currentWeekMon = useMemo(() => startOfWeek(today), [])
  const [weekStart, setWeekStart] = useState(currentWeekMon)

  const slotMap = useMemo(() => new Map(slots.map((day) => [day.value, day])), [slots])
  const timeRows = useMemo(() => {
    const values = [...new Set(slots.flatMap((day) => day.times.map((entry) => timeKey(entry.time))))]
    return (values.length ? values : DEFAULT_TIMES).sort((a, b) => timeAsMinutes(a) - timeAsMinutes(b))
  }, [slots])
  const currentPageStart = useMemo(() => {
    const d = new Date()
    d.setHours(12, 0, 0, 0)
    return d
  }, [])

  const nextMonday = startOfWeek(addDays(currentWeekMon, 7))
  const lastVisibleDate = addDays(currentWeekMon, 60)
  const lastVisibleWeekStart = startOfWeek(lastVisibleDate)
  const isCurrentWeek = dateKey(startOfWeek(weekStart)) <= dateKey(currentWeekMon)
  const isLastVisibleWeek = dateKey(startOfWeek(weekStart)) >= dateKey(lastVisibleWeekStart)
  const todayIndex = (currentPageStart.getDay() + 6) % 7

  const weekDays = useMemo(() => {
    const daysCount = isCurrentWeek ? (7 - todayIndex) : 7
    const startPoint = isCurrentWeek ? currentPageStart : weekStart
    return Array.from({ length: daysCount }, (_, index) => {
      const date = addDays(startPoint, index)
      const key = dateKey(date)
      const source = slotMap.get(key)
      const isPast = key < dateKey(currentPageStart)
      const availableCount = isPast ? 0 : (source?.times.filter((entry) => entry.isAvailable).length || 0)
      const weekdayIdx = isCurrentWeek ? (todayIndex + index) : index
      const isHighlighted = (highlightedDates || []).some((h) => key.endsWith(h) || key.includes(h) || source?.dateLabel?.includes(h))
      return {
        date,
        key,
        source,
        isPast,
        isHighlighted,
        availableCount,
        weekdayIndex: weekdayIdx,
        dayNumber: String(date.getDate()).padStart(2, '0'),
        monthNumber: String(date.getMonth() + 1).padStart(2, '0'),
      }
    })
  }, [slotMap, weekStart, isCurrentWeek, todayIndex, currentPageStart, highlightedDates])

  const weekAvailableCount = weekDays.reduce((total, day) => total + day.availableCount, 0)
  const weekSlotCount = weekDays.reduce((total, day) => total + (day.source?.times.length || 0), 0)
  const weekEnd = weekDays[weekDays.length - 1]?.date || addDays(weekStart, 6)
  const rangeLabel = `${new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit' }).format(weekStart)} – ${new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(weekEnd)}`
  const weekStamp = weekStart.getTime()

  useEffect(() => {
    const current = new Date()
    current.setHours(12, 0, 0, 0)
    // Switching vehicles must keep the requested week, including when the
    // highlighted date is identical to the previous vehicle's selection.
    const [month, day] = String(highlightedDates[0] || '').split('-').map(Number)
    const target = month && day ? new Date(current.getFullYear(), month - 1, day, 12) : current
    setWeekStart(startOfWeek(target))
  }, [car.id, showroom.id])

  useEffect(() => {
    if (pendingSlot?.slotId) {
      const selectedDay = slots.find((day) => day.times.some((entry) => entry.slotId === pendingSlot.slotId))
      if (selectedDay) {
        setWeekStart(startOfWeek(parseDateValue(selectedDay.value)))
      }
    }
  }, [pendingSlot?.slotId, slots])

  // Khi ViVi nhắc đến ngày cụ thể trong chat (highlightedDates), tự động nhảy đến tuần chứa ngày đó.
  // Chỉ nhảy khi highlighted date nằm ở tuần khác với tuần đang xem — không cần nhảy nếu đã đúng tuần.
  useEffect(() => {
    if (!highlightedDates || highlightedDates.length === 0) return
    const currentYear = currentPageStart.getFullYear()
    const firstHighlight = highlightedDates[0] // "MM-DD"
    const [mm, dd] = firstHighlight.split('-').map(Number)
    if (!mm || !dd) return
    const targetDate = new Date(currentYear, mm - 1, dd, 12, 0, 0, 0)
    const targetWeekMon = startOfWeek(targetDate)
    const currentViewWeekMon = startOfWeek(weekStart)
    if (dateKey(targetWeekMon) !== dateKey(currentViewWeekMon)) {
      direction.current = dateKey(targetWeekMon) > dateKey(currentViewWeekMon) ? 1 : -1
      setWeekStart(targetWeekMon)
    }
  }, [JSON.stringify(highlightedDates)])

  useGSAP(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const amount = direction.current * 24
    gsap.fromTo(
      '.schedule-calendar__day, .schedule-calendar__cell',
      { x: amount, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.46, stagger: 0.012, ease: 'power3.out', clearProps: 'transform,opacity' },
    )
    direction.current = 0
  }, { scope: root, dependencies: [weekStamp, slots.length] })

  const changeWeek = (amount) => {
    if (amount < 0 && isCurrentWeek) return
    if (amount > 0 && isLastVisibleWeek) return
    direction.current = Math.sign(amount)
    setWeekStart((current) => {
      const nextDate = addDays(startOfWeek(current), amount * 7)
      const nextMon = startOfWeek(nextDate)
      if (amount < 0 && dateKey(nextMon) <= dateKey(currentWeekMon)) {
        return currentWeekMon
      }
      return nextMon
    })
  }

  const returnToCurrentWeek = () => {
    direction.current = dateKey(currentWeekMon) > dateKey(weekStart) ? 1 : -1
    setWeekStart(currentWeekMon)
  }

  const selectSlot = (event, day, entry) => {
    if (!entry.isAvailable) return
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      gsap.fromTo(event.currentTarget, { scale: 0.96 }, { scale: 1, duration: 0.52, ease: 'elastic.out(1, 0.48)' })
    }
    onPick({ date: day.key, dateLabel: day.source.dateLabel, time: entry.time, slotId: entry.slotId })
  }

  const gridStyle = { gridTemplateColumns: `72px repeat(${weekDays.length}, minmax(118px, 1fr))` }

  return (
    <section className="studio-schedule studio-schedule--calendar" aria-label="Lịch lái thử" aria-busy={calendarLoading} ref={root}>
      {/* Ở chế độ compact (luồng đổi giờ) chỉ còn ĐÚNG một dòng tiêu đề, canh ngang với thanh
          công cụ phía trên. Nhãn "Lịch có đúng mẫu xe" và câu hướng dẫn đã bỏ: cả hai không nói
          thêm gì mà chiếm mất hai dòng ngay phía trên bảng lịch. Lối lùi nay nằm trên thanh
          công cụ chứ không còn ở đây. */}
      {/* Chế độ compact (luồng đổi giờ) KHÔNG in tiêu đề ở đây nữa — nó đã nằm trên thanh công
          cụ để canh đúng hàng với các nút. Nhãn "Lịch có đúng mẫu xe" và câu hướng dẫn cũng bỏ:
          cả hai chiếm hai dòng ngay trên bảng lịch mà không nói thêm được gì. */}
      {!compact && (
        <div className="studio-schedule__heading">
          <span>Lịch có đúng mẫu xe</span>
          <h2>{car.name} tại {showroom.name}</h2>
          <p>Chọn trực tiếp một ô còn xe. Bạn có thể chuyển tuần để xem những ngày xa hơn.</p>
        </div>
      )}

      {calendarLoading && <p role="status">Đang tải đầy đủ lịch của mẫu xe tại showroom…</p>}
      {calendarError && <p role="alert">{calendarError} Các ô chưa tải không có nghĩa là hết lịch.</p>}
      <div className="schedule-calendar">
        <header className="schedule-calendar__toolbar">
          <div className="schedule-calendar__navigation" aria-label="Điều hướng tuần">
            <button type="button" onClick={() => changeWeek(-1)} disabled={disabled || isCurrentWeek} aria-label="Xem tuần trước"><CaretLeft size={17} weight="bold" /></button>
            <button type="button" onClick={returnToCurrentWeek} disabled={disabled || isCurrentWeek}>Tuần này</button>
            <button type="button" onClick={() => changeWeek(1)} disabled={disabled || isLastVisibleWeek} aria-label="Xem tuần sau"><CaretRight size={17} weight="bold" /></button>
          </div>
          <div className="schedule-calendar__range">
            <strong>{rangeLabel}</strong>
            <small>{calendarIncomplete ? 'Lịch đang hiển thị chưa đầy đủ' : weekAvailableCount ? `${weekAvailableCount} khung giờ còn xe` : 'Chưa có lịch trống trong tuần này'}</small>
          </div>
          {!compact && (
            <div className="schedule-calendar__legend" aria-label="Chú thích trạng thái">
              <span><i className="is-available" /> Còn xe</span>
              <span><i className="is-unavailable" /> Đã kín</span>
            </div>
          )}
        </header>

        <div className="schedule-calendar__viewport">
          <div className="schedule-calendar__matrix" role="grid" aria-label={`Lịch tuần ${rangeLabel}`}>
            <div className="schedule-calendar__week" style={gridStyle} role="row">
              <div className="schedule-calendar__time-title" role="columnheader"><Clock size={15} weight="light" /> Giờ</div>
              {weekDays.map((day) => {
                const isToday = dateKey(new Date()) === day.key
                return (
                  <div className={`schedule-calendar__day ${isToday ? 'is-today' : ''} ${day.isPast ? 'is-past' : ''} ${day.isHighlighted ? 'is-highlighted' : ''}`.trim()} role="columnheader" key={day.key}>
                    <span>{WEEKDAY_LABELS[day.weekdayIndex]}</span>
                    <strong>{day.dayNumber}</strong>
                    {/* Bỏ dòng đếm "N lịch" và dòng tháng: số lịch đã hiện ngay
                        trong lưới khung giờ bên dưới, nhắc lại ở đây chỉ làm ô
                        ngày rối và đẩy thứ với số ngày xa nhau.
                        Giữ lại đúng "Đã qua": đó là lý do ô bị khoá, không nói
                        thì người dùng bấm mãi không hiểu vì sao không được. */}
                    {day.isPast && <small>Đã qua</small>}
                  </div>
                )
              })}
            </div>

            <div className="schedule-calendar__body">
              {timeRows.map((time) => (
                <div className="schedule-calendar__row" style={gridStyle} role="row" key={time}>
                  <div className="schedule-calendar__time" role="rowheader">{time}</div>
                  {weekDays.map((day) => {
                    const entry = day.source?.times.find((candidate) => timeKey(candidate.time) === time)
                    const active = entry && pendingSlot?.slotId === entry.slotId
                    const available = !day.isPast && Boolean(entry?.isAvailable)
                    return (
                      <div className="schedule-calendar__cell" role="gridcell" key={`${day.key}-${time}`}>
                        {entry ? (
                          <button
                            type="button"
                            disabled={disabled || !available}
                            className={`${available ? 'is-available' : 'is-unavailable'} ${active ? 'is-active' : ''}`.trim()}
                            onClick={(event) => available && selectSlot(event, day, entry)}
                            aria-label={`${entry.time}, ${day.source.dateLabel}: ${entry.isAvailable ? `${car.name} còn xe` : entry.unavailableLabel}`}
                          >
                            <span />
                            <strong>{entry.isAvailable ? (compact ? 'Còn xe' : `Có ${car.name}`) : entry.unavailableLabel}</strong>
                            {!compact && <small>{entry.isAvailable ? 'Sẵn sàng lái thử' : 'Không thể chọn'}</small>}
                          </button>
                        ) : <span className="schedule-calendar__empty-cell" aria-label={calendarIncomplete ? 'Chưa tải đủ lịch' : 'Showroom chưa mở lịch'} />}
                      </div>
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {!weekSlotCount && !calendarIncomplete && (
          <div className="schedule-calendar__empty">
            <CalendarBlank size={19} weight="light" />
            <span><strong>Showroom chưa mở lịch cho tuần này.</strong><small>Chuyển sang tuần khác hoặc nhắn ViVi ngày bạn mong muốn.</small></span>
          </div>
        )}
      </div>
    </section>
  )
}

/**
 * BookingNextSteps — hướng dẫn sau khi đặt lịch thành công.
 *
 * Rút về ĐÚNG BA việc người vừa đặt lịch cần làm (anh Minh chốt 17/08/2026):
 * mang giấy phép lái xe · xưng danh ở quầy lễ tân · có mặt sớm 15 phút.
 * Bản trước có bốn mục kèm địa chỉ, chỉ đường, tư vấn viên, hotline, lịch nhắc — những thứ đó
 * đã nằm nguyên trên phiếu lịch ở màn hình bên trái, lặp lại ở đây chỉ làm loãng.
 *
 * QUY TẮC NỘI DUNG giữ nguyên: mỗi dòng phải có nguồn dữ liệu thật, không bịa quy trình.
 * Tên người lái lấy từ form; giờ hẹn lấy từ `slot`. KHÔNG in mã lịch ở đây nữa — lễ tân tra
 * bằng tên, số điện thoại và email đã đăng ký, người dùng không phải nhớ mã.
 *
 * TODO [BACKEND/BOOKING]: chưa có API nào trả hạng GPLX yêu cầu cho mẫu xe
 * (`vehicle_models.required_license_class` có trong DB nhưng không xuất hiện ở
 * GET /vehicles/{id}), nên mục "Mang theo" chỉ nói "đúng hạng" chứ không nêu hạng cụ thể.
 */
/** Người dùng nên tới sớm chừng này để làm thủ tục và được nhân viên đón tiếp. */
const ARRIVE_EARLY_MINUTES = 15

export function BookingNextSteps({ slot, person, recipient }) {
  const driverName = recipient === 'other' ? person.driverName : person.bookingName
  const contactName = person.bookingName
  const contactPhone = person.phone
  const contactEmail = person.email

  return (
    <section className="booking-next-steps" aria-labelledby="booking-next-steps-title">
      <h2 id="booking-next-steps-title">Ba việc bạn cần lưu ý trước buổi lái thử</h2>

      <ol className="booking-next-steps__list">
        <li>
          <span className="booking-next-steps__label">Giấy tờ mang theo</span>
          <p>
            Bạn nhớ mang theo <strong>giấy phép lái xe</strong> còn hiệu lực và đúng hạng với mẫu xe
            đã đăng ký. Giấy phép cần mang tên <strong>{driverName || 'người lái thử'}</strong>,
            trùng với thông tin bạn vừa điền.
          </p>
        </li>

        <li>
          <span className="booking-next-steps__label">Khi tới quầy lễ tân</span>
          <p>
            Bạn chỉ cần đọc tên, số điện thoại và email đã đăng ký cho lễ tân là được. Bạn không cần
            nhớ mã lịch, vì showroom tra được bằng ba thông tin này.
          </p>
          <p className="booking-next-steps__muted">
            {[contactName, contactPhone, contactEmail].filter(Boolean).join(' · ')}
          </p>
        </li>

        <li>
          <span className="booking-next-steps__label">Thời gian có mặt</span>
          <p>
            Bạn nên có mặt trước giờ hẹn ít nhất <strong>{ARRIVE_EARLY_MINUTES} phút</strong> để
            làm thủ tục, và để nhân viên showroom có thời gian đón tiếp bạn chu đáo.
          </p>
          {slot?.time && slot?.dateLabel && (
            <p className="booking-next-steps__muted">
              Giờ hẹn của bạn là {slot.time}, {slot.dateLabel}.
            </p>
          )}
        </li>
      </ol>
    </section>
  )
}

export function buildGoogleCalendarUrl({ car, showroom, slot, bookingCode, advisor }) {
  if (!car || !showroom || !slot) return ''

  const title = `Lái thử xe VinFast ${car.name}`
  const location = `${showroom.name} - ${showroom.address}`
  const details = `Mã đặt lịch: ${bookingCode || 'Tạm giữ'}\nMẫu xe: ${car.name}\nShowroom: ${showroom.name}\nTư vấn viên: ${advisor?.full_name || 'VinFast Advisor'}`

  let startTimeStr = ''
  let endTimeStr = ''

  if (slot.startAt) {
    const startDate = new Date(slot.startAt)
    const endDate = slot.endAt ? new Date(slot.endAt) : new Date(startDate.getTime() + 45 * 60000)
    if (!isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
      startTimeStr = startDate.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
      endTimeStr = endDate.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
    }
  } else if (slot.date && slot.time) {
    const timeClean = slot.time.length === 5 ? slot.time : slot.time.padStart(5, '0')
    const startDate = new Date(`${slot.date}T${timeClean}:00+07:00`)
    if (!isNaN(startDate.getTime())) {
      const endDate = new Date(startDate.getTime() + 45 * 60000)
      startTimeStr = startDate.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
      endTimeStr = endDate.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
    }
  }

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: title,
    details,
    location,
    ctz: 'Asia/Ho_Chi_Minh',
    ...(startTimeStr && endTimeStr ? { dates: `${startTimeStr}/${endTimeStr}` } : {}),
  })

  return `https://calendar.google.com/calendar/render?${params.toString()}`
}

/**
 * Dán hai chữ cuối lại với nhau bằng khoảng trắng không ngắt.
 *
 * Ô giá trị trong phiếu hẹp (lưới hai cột, nhãn đã chiếm 100px), nên chuỗi dài
 * tự xuống dòng và hay bỏ lại đúng MỘT chữ ở hàng cuối: "VinFast Nguyễn Văn"
 * rồi "Cừ" đứng lẻ loi. Đây là thứ chủ dự án ghét nhất trong cả màn này.
 *
 * Không vá từng ca: chỉ cần chữ cuối luôn đi cùng chữ áp cuối là mọi chuỗi đều
 * hết rớt lẻ, dù dài ngắn ra sao. Chuỗi một chữ thì giữ nguyên.
 *
 * Dùng kèm `text-wrap: pretty` bên CSS. Hai thứ bù nhau: CSS lo mấy đoạn văn dài
 * mà mã không đi qua được, còn hàm này lo đúng chỗ nhạy nhất là ô giá trị.
 */
const noOrphan = (value) => {
  if (typeof value !== 'string') return value
  const words = value.trim().split(/\s+/)
  if (words.length < 2) return value
  return `${words.slice(0, -1).join(' ')}\u00A0${words[words.length - 1]}`
}

export function BookingTicket({ car, showroom, slot, person, recipient, bookingCode, advisor = null, compact = false }) {
  const advisorLabel = advisor?.full_name
    ? `${advisor.full_name}${advisor.phone ? ` · ${advisor.phone}` : ''}`
    : bookingCode
      ? 'Chưa phân công'
      : 'Sẽ được phân công khi xác nhận'
  // Đặt hộ và người lái có liên hệ riêng: phiếu phải nói rõ AI nhận thông báo nào,
  // nếu không showroom sẽ gọi nhầm người đặt trong khi người cầm lái không hay biết.
  const bookingForOther = recipient === 'other'
  const driverHasOwnContact = bookingForOther && person.driverSameContact === false
  const contactLine = (phone, email) => [phone, email].filter(Boolean).join(' · ') || 'Chưa có thông tin liên hệ'

  const mapsUrl = (showroom.latitude && showroom.longitude)
    ? `https://www.google.com/maps/search/?api=1&query=${showroom.latitude},${showroom.longitude}`
    : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(showroom.name + ' ' + (showroom.address || ''))}`

  const showroomElement = (
    <a
      href={mapsUrl}
      target="_blank"
      rel="noopener noreferrer"
      style={{ color: '#0C64E6', textDecoration: 'underline', fontWeight: 600 }}
      title="Bấm để mở vị trí và chỉ đường trên Google Maps"
    >
      {noOrphan(`${showroom.name} ↗`)}
    </a>
  )

  const rows = [
    ['Người đặt lịch', person.bookingName],
    ['Liên hệ người đặt', contactLine(person.phone, person.email)],
    ['Người lái thử', bookingForOther ? person.driverName : person.bookingName],
    ...(bookingForOther
      ? [['Liên hệ người lái', driverHasOwnContact
          ? contactLine(person.driverPhone, person.driverEmail)
          : 'Dùng chung liên hệ với người đặt']]
      : []),
    ['Mẫu xe', car.name],
    ['Showroom', showroomElement],
    ['Thời gian', `${slot.time} · ${slot.dateLabel}`],
    ['Tư vấn viên', advisorLabel],
  ]

  return (
    <section className={`studio-ticket ${compact ? 'studio-ticket--compact' : ''}`}>
      <header>
        <span>{bookingCode ? 'Lịch lái thử đã xác nhận' : 'Kiểm tra trước khi đặt lịch'}</span>
        {bookingCode && <strong>{bookingCode}</strong>}
      </header>
      <div className="studio-ticket__vehicle">
        <VehicleShot car={car} mode="cutout" />
        <span><strong>{car.name}</strong><small>{car.body}</small></span>
      </div>
      <dl>
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{noOrphan(label)}</dt>
            <dd>{noOrphan(value)}</dd>
          </div>
        ))}
      </dl>
      <p><CheckCircle size={16} weight="fill" /> {noOrphan('Đã xác nhận có giấy phép lái xe phù hợp.')}</p>
    </section>
  )
}
