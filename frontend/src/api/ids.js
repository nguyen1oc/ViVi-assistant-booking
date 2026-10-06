/**
 * api/ids.js — Sinh mã định danh duy nhất cho mỗi thao tác đặt lịch (`ui_action_id`).
 *
 * VÌ SAO KHÔNG GỌI THẲNG crypto.randomUUID()
 * `crypto.randomUUID` CHỈ tồn tại trong "secure context": HTTPS, localhost hoặc 127.0.0.1.
 * Mở web bằng địa chỉ mạng LAN (ví dụ http://192.168.0.105:3000 — chính là địa chỉ Vite in ra
 * dòng "Network:", cũng là địa chỉ dùng để test trên điện thoại) thì nó là `undefined`, và
 * toàn bộ luồng giữ chỗ chết với lỗi "crypto.randomUUID is not a function".
 *
 * `crypto.getRandomValues` thì CÓ ở cả secure lẫn non-secure context, nên đây là chỗ dựa chính.
 * Đã đo thực tế bằng trình duyệt:
 *   http://localhost:3000      -> isSecureContext true,  randomUUID: function
 *   http://192.168.0.105:3000  -> isSecureContext false, randomUUID: undefined, getRandomValues: function
 *
 * Mã này đi vào `ui_action_id` mà backend dùng để chống đặt trùng, nên phải thật sự ngẫu nhiên.
 * Nhánh dự phòng cuối cùng (Math.random) chỉ dành cho trình duyệt quá cũ không có Web Crypto;
 * nó yếu hơn nhưng vẫn kèm timestamp nên không đụng nhau trong thực tế.
 */

const toHex = (bytes) => Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')

/** UUID v4 dựng từ getRandomValues — chạy được cả khi không phải secure context. */
const uuidFromRandomValues = () => {
  const bytes = new Uint8Array(16)
  globalThis.crypto.getRandomValues(bytes)
  bytes[6] = (bytes[6] & 0x0f) | 0x40 // đánh dấu version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80 // đánh dấu variant RFC 4122
  const hex = toHex(bytes)
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

/** Trình duyệt quá cũ, không có Web Crypto. Kém ngẫu nhiên hơn nên để cuối cùng. */
const uuidFallback = () => {
  const random = () => Math.floor(Math.random() * 0xffffffff).toString(16).padStart(8, '0')
  return `${random()}-${Date.now().toString(16).slice(-8)}-${random().slice(0, 4)}-${random()}`
}

/** Trả về một UUID, tự chọn cách sinh tốt nhất mà trình duyệt hiện có. */
export function randomId() {
  const webCrypto = globalThis.crypto
  if (typeof webCrypto?.randomUUID === 'function') return webCrypto.randomUUID()
  if (typeof webCrypto?.getRandomValues === 'function') return uuidFromRandomValues()
  return uuidFallback()
}

/** Mã thao tác gửi lên backend, ví dụ actionId('hold') -> 'hold:3f2a...'. */
export const actionId = (prefix) => `${prefix}:${randomId()}`
