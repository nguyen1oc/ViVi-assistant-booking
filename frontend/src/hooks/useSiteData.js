/**
 * hooks/useSiteData.js — 3 hook để các trang lấy dữ liệu backend mà không phải tự viết fetch.
 *
 * Mỗi hook tự lo: gọi API → đổi tên trường qua adapters → trả về { loading, error }
 * và tự huỷ request khi người dùng rời trang (AbortController).
 *
 * Chứa gì:
 * - useVehicleCatalog(): danh sách xe, đã sắp xếp theo sortOrder của backend.
 *   Dùng ở HomePage, CarDetailPage (để tìm "xe tiếp theo") và BookingPage.
 * - useVehicleDetail(id): chi tiết một mẫu xe. Dùng ở CarDetailPage.
 * - usePageContent(page): nội dung trang home / charging / after-sales.
 * - useBookingUpsell(): 2 mẫu xe sale admin đang muốn đẩy, hiện ở khung chat đặt lịch.
 *
 * LƯU Ý: không có dữ liệu dự phòng. Backend chết thì cars = [] và trang hiện rỗng —
 * đây là chủ ý để giao diện không bịa ra catalogue giả.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { getPageContent } from '../api/content'
import { vehicleDetailToCar, vehicleSummaryToCar } from '../api/adapters'
import { getVehicle, getVehicles } from '../api/vehicles'
import { DEFAULT_UPSELL_VEHICLE_IDS, getBookingUpsell, normalizeUpsellConfig } from '../api/upsell'
import { withSupplementalColors } from '../data/vehicle-colors'

export function useVehicleCatalog() {
  const [remote, setRemote] = useState(null)
  const [error, setError] = useState(null)
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setRemote(null)
    setError(null)
    getVehicles({}, { signal: controller.signal })
      .then((items) => setRemote(items.map(vehicleSummaryToCar)))
      .catch((reason) => {
        if (reason.name !== 'AbortError') setError(reason)
      })
    return () => controller.abort()
  }, [retryKey])

  const cars = useMemo(
    () => [...(remote || [])].sort((left, right) => (left.sortOrder || 0) - (right.sortOrder || 0)),
    [remote],
  )

  const retry = useCallback(() => setRetryKey((key) => key + 1), [])

  return {
    cars,
    loading: remote === null && error === null,
    error,
    retry,
    source: remote ? 'backend' : 'unavailable',
  }
}

/**
 * useBookingUpsell() — đọc 2 mẫu xe mà sale admin chọn để upsell trong khung chat ViVi.
 *
 * Khác với useVehicleCatalog: hook này CÓ giá trị mặc định. Lý do là nó đọc một tuỳ chọn
 * cấu hình chứ không đọc dữ liệu xe. Backend chưa gắn endpoint, hoặc admin chưa cấu hình,
 * thì màn đặt lịch vẫn phải mời được khách chọn xe thay vì hiện một khoảng trống.
 * Thông tin từng chiếc xe vẫn do useVehicleCatalog lấy từ backend, hook này chỉ trả về id.
 */
export function useBookingUpsell() {
  const [config, setConfig] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    getBookingUpsell({ signal: controller.signal })
      .then((payload) => setConfig(normalizeUpsellConfig(payload)))
      .catch((reason) => {
        if (reason.name === 'AbortError') return
        // Không chặn luồng đặt lịch vì một tuỳ chọn hiển thị. Ghi lỗi lại để trang admin
        // biết cấu hình chưa về được, còn khách vẫn thấy cặp xe mặc định.
        setError(reason)
        setConfig(normalizeUpsellConfig(null))
      })
    return () => controller.abort()
  }, [])

  return {
    vehicleIds: config?.vehicleIds || DEFAULT_UPSELL_VEHICLE_IDS,
    headline: config?.headline || '',
    note: config?.note || '',
    // 'admin' = admin đã cấu hình, 'default' = đang chạy cặp mặc định.
    source: config?.configured ? 'admin' : 'default',
    loading: config === null,
    error,
  }
}

export function useVehicleDetail(vehicleId) {
  const [car, setCar] = useState(null)
  const [error, setError] = useState(null)
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setCar(null)
    setError(null)
    getVehicle(vehicleId, { signal: controller.signal })
      .then((vehicle) => setCar(vehicleDetailToCar(vehicle)))
      .catch((reason) => {
        if (reason.name !== 'AbortError') setError(reason)
      })
    return () => controller.abort()
  }, [vehicleId, retryKey])

  const retry = useCallback(() => setRetryKey((key) => key + 1), [])

  return { car, loading: !car && !error, error, retry }
}

const hexColorPattern = /^#[0-9a-f]{6}$/i

/**
 * useVehicleColorOptions(ids) — bảng màu ngoại thất cho các mẫu xe ĐANG hiển thị trên trang chủ.
 *
 * TODO [BACKEND/CATALOGUE]: GET /vehicles KHÔNG trả `colorOptions` (kiểm tra 16/08/2026: field
 * về đúng `null`), trong khi GET /vehicles/{id} thì có. Vì vậy trang chủ buộc phải gọi thêm một
 * request cho mỗi xe đang hiện — đúng kiểu N+1 mà bình thường phải tránh. Khi backend trả
 * `colorOptions` trong summary thì XOÁ hook này và đọc thẳng `car.colorOptions` trong adapters.
 *
 * Giảm thiệt hại: chỉ gọi cho các xe thuộc tab đang mở, và apiGet có cache theo `vehicle:<id>`
 * nên rê chuột vào thẻ hoặc mở trang chi tiết sau đó không tạo request mới.
 *
 * Mẫu backend chưa publish màu thì lấy từ `data/vehicle-colors.js` (bảng màu chính hãng chép
 * từ vinfast.vn). Còn 4 mẫu thật sự chưa có nguồn nào — VF 6, VF MPV 7, Nerio Green, eBus —
 * trả mảng rỗng để giao diện hiện "Đang cập nhật", KHÔNG tự bịa swatch.
 *
 * Một màu hợp lệ khi có `hex` (backend) HOẶC `swatch` là ảnh chip (bảng bổ sung). Sơn xe có
 * kim loại nên nhiều màu không quy về hex phẳng được — chính vinfast.vn cũng vẽ swatch bằng ảnh.
 */
export function useVehicleColorOptions(vehicleIds) {
  const [colorsById, setColorsById] = useState({})
  const idKey = vehicleIds.join(',')

  useEffect(() => {
    if (!idKey) return undefined
    const controller = new AbortController()
    let active = true

    Promise.all(idKey.split(',').map((id) => (
      getVehicle(id, { signal: controller.signal })
        .then((vehicle) => [id, withSupplementalColors(id, (vehicle.colors || [])
          .filter((color) => color?.name && hexColorPattern.test(color?.hex || ''))
          .map((color) => ({
            name: String(color.name),
            hex: color.hex,
            secondaryHex: hexColorPattern.test(color.secondaryHex || '') ? color.secondaryHex : null,
          })))])
        // Một xe lỗi thì chỉ xe đó mất swatch, không kéo sập cả dải.
        .catch(() => [id, []])
    ))).then((entries) => {
      if (active) setColorsById((current) => ({ ...current, ...Object.fromEntries(entries) }))
    })

    return () => {
      active = false
      controller.abort()
    }
  }, [idKey])

  return colorsById
}

export function usePageContent(page) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    getPageContent(page, { signal: controller.signal })
      .then(setData)
      .catch((reason) => {
        if (reason.name !== 'AbortError') setError(reason)
      })
    return () => controller.abort()
  }, [page])

  return { data, loading: data === null && error === null, error }
}
