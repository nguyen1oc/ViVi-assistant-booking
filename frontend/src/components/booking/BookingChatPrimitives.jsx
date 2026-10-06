/**
 * components/booking/BookingChatPrimitives.jsx — Các mảnh giao diện của khung chat ViVi.
 *
 * - ViViAvatar: ảnh đại diện ViVi, prop `compact` cho bản nhỏ nằm cạnh tin nhắn.
 * - AgentMessage: một bong bóng tin nhắn với hiệu ứng gõ chữ và định vị dòng/chữ in đậm.
 * - ViviStatusTyping: chỉ báo hiệu ứng "ViVi đang thực hiện tác vụ cho bạn".
 * - ContextualChoices: dải nút gợi ý ngay trong khung chat (Showroom / Slot).
 */
import { useEffect, useRef, useState } from 'react'
import { Clock, MapPin } from '@phosphor-icons/react'
import { viviAvatar } from '../../data/media'

const formatDistance = (distance) => (
  Number.isFinite(distance) ? `${String(distance).replace('.', ',')} km` : ''
)

export function ViViAvatar({ compact = false }) {
  return (
    <span className={`${compact ? 'vivi-message__avatar' : 'vivi-studio__avatar'} vivi-avatar`}>
      <img src={viviAvatar} alt="" aria-hidden="true" />
    </span>
  )
}

export function AgentMessage({ message, isLatest, onTypingComplete }) {
  const [displayedText, setDisplayedText] = useState(
    isLatest && message.role === 'assistant' ? '' : (message.text || '')
  )
  const [isTyping, setIsTyping] = useState(false)
  const hasAnimatedRef = useRef(false)
  const textRef = useRef(message.text)

  useEffect(() => {
    textRef.current = message.text
  }, [message.text])

  useEffect(() => {
    if (message.role !== 'assistant' || !isLatest || hasAnimatedRef.current) return

    const initialText = textRef.current || ''
    if (!initialText) return

    hasAnimatedRef.current = true
    setDisplayedText('')
    setIsTyping(true)
    let index = 0

    const timer = setInterval(() => {
      const currentFullText = textRef.current || ''
      index = Math.min(index + 1, currentFullText.length)
      setDisplayedText(currentFullText.slice(0, index))
      if (index >= currentFullText.length) {
        clearInterval(timer)
        setIsTyping(false)
        onTypingComplete?.(message.id)
      }
    }, 16)

    return () => {
      clearInterval(timer)
      setIsTyping(false)
    }
  }, [message.id, message.role, isLatest, onTypingComplete])

  useEffect(() => {
    if (!isTyping) {
      setDisplayedText(message.text || '')
    }
  }, [message.text, isTyping])

  const formatText = (text) => {
    if (!text) return null
    return text.split('\n').map((line, i) => {
      const html = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      return (
        <span
          key={i}
          style={{ display: 'block', minHeight: '1em' }}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )
    })
  }

  return (
    <div
      className={`vivi-message vivi-message--${message.role} ${message.emphasis ? 'vivi-message--emphasis' : ''}`.trim()}
      data-message-id={message.id}
    >
      {message.role === 'assistant' && <ViViAvatar compact />}
      <div>
        <p>{formatText(displayedText)}</p>
      </div>
    </div>
  )
}

export function ViviStatusTyping() {
  const words = ['ViVi', 'đang', 'thực', 'hiện', 'tác', 'vụ', 'cho', 'bạn']

  return (
    <div className="vivi-typing" aria-label="ViVi đang thực hiện tác vụ cho bạn">
      {words.map((word, index) => (
        <span
          key={`${word}-${index}`}
          className="vivi-typing__word"
          style={{ animationDelay: `${(index * 0.1).toFixed(1)}s` }}
        >
          {word}
        </span>
      ))}
      <span className="vivi-typing__dot" style={{ animationDelay: '0.8s' }} />
      <span className="vivi-typing__dot" style={{ animationDelay: '0.9s' }} />
      <span className="vivi-typing__dot" style={{ animationDelay: '1.0s' }} />
    </div>
  )
}

export function ContextualChoices({ stage, allowedActions, car, locationSuggestions, showrooms, slots, pendingSlot, highlightedDates = [], disabled = false, onResolveArea, onShowroom, onSlot }) {
  if (!car) return null

  if (stage === 'need_address' || stage === 'need_ward') {
    return null
  }

  if (stage === 'choose_showroom' && allowedActions.includes('select_showroom') && showrooms.length) {
    return (
      <div className="agent-context" aria-label="Chọn showroom trong cuộc trò chuyện">
        <div className="agent-context__heading"><span>Showroom phù hợp</span><small>Đã ưu tiên có xe trước, khoảng cách sau</small></div>
        <div className="agent-context__rail">
          {showrooms.slice(0, 4).map((showroom) => (
            <button type="button" key={showroom.id} onClick={() => onShowroom(showroom)} disabled={disabled}>
              <span><MapPin size={16} weight="light" /></span>
              <strong>{showroom.name.replace('VinFast ', '')}</strong>
              <small>{formatDistance(showroom.distance) ? `${formatDistance(showroom.distance)} · ` : ''}Có {car.name}</small>
            </button>
          ))}
        </div>
      </div>
    )
  }

  if (stage === 'choose_slot' && allowedActions.includes('select_slot') && slots.length) {
    const availableDays = slots.filter((day) => day.times.some((entry) => entry.isAvailable))
    const targetKeys = highlightedDates
    const matchedDays = []

    if (pendingSlot?.slotId) {
      const pDay = availableDays.find((day) => day.times.some((entry) => entry.slotId === pendingSlot.slotId))
      if (pDay) matchedDays.push(pDay)
    }

    if (!matchedDays.length && targetKeys.length) {
      for (const key of targetKeys) {
        const found = availableDays.find((day) => day.value?.endsWith(`-${key}`) || day.dateLabel?.includes(key.replace('-', '/')))
        if (found && !matchedDays.some((d) => d.value === found.value)) {
          matchedDays.push(found)
        }
      }
    }

    const quickSlots = []
    const targetDays = matchedDays.length ? matchedDays : availableDays

    for (const day of targetDays) {
      const avail = day.times.filter((entry) => entry.isAvailable)
      // Loại bỏ các mốc giờ trùng lặp trên cùng 1 ngày (ví dụ 09:00 có ở cả bản Eco và Plus)
      const seenTimes = new Set()
      for (const entry of avail) {
        if (!seenTimes.has(entry.time)) {
          seenTimes.add(entry.time)
          quickSlots.push({
            date: day.value,
            dateLabel: day.dateLabel,
            time: entry.time,
            slotId: entry.slotId,
          })
          if (quickSlots.length >= 5) break
        }
      }
      if (quickSlots.length >= 5) break
    }

    const displaySlots = quickSlots.slice(0, 5)

    return (
      <div className="agent-context" aria-label="Khung giờ còn trống">
        <div className="agent-context__heading"><span>Khung giờ gần nhất</span><small>Đã ghép đúng xe {car.name}</small></div>
        <div className="agent-context__rail agent-context__rail--slots">
          {displaySlots.map((slot, idx) => (
            <button type="button" key={slot.slotId || `${slot.date}-${slot.time}-${idx}`} onClick={() => onSlot(slot)} disabled={disabled}>
              <span><Clock size={16} weight="light" /></span>
              <strong>{slot.time}</strong>
              <small>{slot.dateLabel}</small>
            </button>
          ))}
        </div>
      </div>
    )
  }

  return null
}
