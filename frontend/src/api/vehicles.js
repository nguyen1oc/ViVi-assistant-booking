/**
 * api/vehicles.js — Lấy danh sách xe và chi tiết một mẫu xe từ backend.
 *
 * Gọi tới: GET /api/v1/vehicles  và  GET /api/v1/vehicles/{id}
 *
 * Chứa gì:
 * - getVehicles(filters): danh sách xe cho trang chủ, menu và bảng đổi xe.
 *   filters có thể lọc theo category / featured / testDriveEligible.
 * - getVehicle(id): dữ liệu đầy đủ một mẫu xe cho trang chi tiết (thông số, màu, ảnh, brochure).
 * - prefetchVehicle(id): tải trước khi người dùng rê chuột vào thẻ xe, để bấm vào mở nhanh hơn.
 *
 * Dữ liệu thô ở đây chưa dùng thẳng được cho giao diện — phải qua api/adapters.js đổi tên trường.
 */
import { apiGet } from './client'

const toQuery = (filters) => {
  const query = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ''
}

export const getVehicles = (filters = {}, options = {}) => {
  const query = toQuery(filters)
  return apiGet(`/vehicles${query}`, { ...options, cacheKey: `vehicles:${query}` })
}

export const getVehicle = (vehicleId, options = {}) =>
  apiGet(`/vehicles/${encodeURIComponent(vehicleId)}`, { ...options, cacheKey: `vehicle:${vehicleId}` })

export const prefetchVehicle = (vehicleId) => getVehicle(vehicleId).catch(() => undefined)
