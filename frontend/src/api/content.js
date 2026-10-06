/**
 * api/content.js — Lấy NỘI DUNG BIÊN TẬP của 3 trang marketing từ backend.
 *
 * Gọi tới: GET /api/v1/content/{page} — chỉ chấp nhận 3 giá trị: home, charging, after-sales.
 *
 * Trả về những thứ backend quản lý thay vì hard-code trong frontend, ví dụ:
 * - home: hero (xe nào làm ảnh chính), video, các khối editorial, testimonial.
 * - charging: danh mục trụ sạc (chargingUnits), giá điện, mạng lưới.
 * - after-sales: bảng thời hạn bảo hành pin (warrantyTables).
 *
 * Truyền tên trang không nằm trong danh sách sẽ ném lỗi ngay — cố ý để bắt lỗi gõ sai sớm.
 */
import { apiGet } from './client'

const allowedPages = new Set(['home', 'charging', 'after-sales'])

export function getPageContent(page, options = {}) {
  if (!allowedPages.has(page)) throw new Error(`Unsupported content page: ${page}`)
  return apiGet(`/content/${page}`, { ...options, cacheKey: `content:${page}` })
}
