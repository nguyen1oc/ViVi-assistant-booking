/**
 * Một nguồn duy nhất cho các quyết định khác biệt theo năng lực thiết bị.
 * Layout vẫn do CSS/media query sở hữu; JS chỉ dùng để hạ chuyển động hoặc tránh tải
 * WebGL nặng khi người dùng bật tiết kiệm dữ liệu hay thiết bị có tài nguyên thấp.
 */
export function getClientDeviceProfile() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return {
      compact: false,
      constrained: false,
      reducedMotion: false,
    }
  }

  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection
  const effectiveType = connection?.effectiveType || ''
  const compact = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const lowMemory = Number.isFinite(navigator.deviceMemory) && navigator.deviceMemory <= 2
  const lowCpu = Number.isFinite(navigator.hardwareConcurrency) && navigator.hardwareConcurrency <= 2
  const slowNetwork = effectiveType === 'slow-2g' || effectiveType === '2g'

  return {
    compact,
    reducedMotion,
    constrained: connection?.saveData === true || slowNetwork || (compact && (lowMemory || lowCpu)),
  }
}
