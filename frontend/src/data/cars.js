/**
 * data/cars.js — Định nghĩa 2 NHÓM XE hiển thị trên web. File rất ngắn nhưng ảnh hưởng rộng.
 *
 * Toàn bộ danh sách xe nay lấy từ backend (GET /api/v1/vehicles). File này chỉ còn giữ
 * phần backend không quản: tên và mô tả của 2 nhóm dùng để chia tab/chia mục.
 *
 * carGroups:
 * - 'personal' → "Động cơ điện"    (dải xe cá nhân VF 3 … VF 9)
 * - 'fleet'    → "Dòng xe dịch vụ" (Green, giao vận, vận tải công cộng)
 * `id` phải khớp đúng trường `category` backend trả về, sai một chữ là nhóm đó trống rỗng.
 *
 * Dùng ở: HomePage (2 tab dải xe), BookingPage và VehicleWorkspace (bảng đổi xe).
 * carImage chỉ là tên gọi khác của vehicleImage trong media/assets.js, giữ cho code cũ chạy được.
 */
import { vehicleImage } from '../media/assets'

export const carImage = vehicleImage

export const carGroups = [
  {
    id: 'personal',
    label: 'Động cơ điện',
    description: 'Từ mini eSUV đến SUV điện ba hàng ghế.',
  },
  {
    id: 'fleet',
    label: 'Dòng xe dịch vụ',
    description: 'Dải Green, giao vận và vận tải công cộng.',
  },
]
