export const NAME_MAX_LENGTH = 30
export const PHONE_LENGTH = 10
export const EMAIL_LOCAL_MAX_LENGTH = 30
export const EMAIL_DOMAIN_MAX_LENGTH = 20
export const EMAIL_MAX_LENGTH = EMAIL_LOCAL_MAX_LENGTH + 1 + EMAIL_DOMAIN_MAX_LENGTH

export const limitName = (value = '') => String(value).slice(0, NAME_MAX_LENGTH)

export const limitPhone = (value = '') => {
  const digits = String(value).replace(/\D/g, '')
  const localDigits = digits.startsWith('84') ? `0${digits.slice(2)}` : digits
  return localDigits.slice(0, PHONE_LENGTH)
}

export const limitEmail = (value = '') => {
  const text = String(value)
  const separator = text.indexOf('@')
  if (separator < 0) return text.slice(0, EMAIL_LOCAL_MAX_LENGTH)
  const local = text.slice(0, separator).slice(0, EMAIL_LOCAL_MAX_LENGTH)
  const domain = text.slice(separator + 1).slice(0, EMAIL_DOMAIN_MAX_LENGTH)
  return `${local}@${domain}`
}

export const isLimitedEmail = (value = '') => {
  const text = String(value).trim()
  const parts = text.split('@')
  if (parts.length !== 2) return false
  const [local, domain] = parts
  return Boolean(local && domain)
    && local.length <= EMAIL_LOCAL_MAX_LENGTH
    && domain.length <= EMAIL_DOMAIN_MAX_LENGTH
    && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)
}

export const isTenDigitPhone = (value = '') => /^0\d{9}$/.test(String(value).trim())
