/**
 * components/booking/ShowroomMap.jsx — Bản đồ chọn showroom (bước 3 của luồng đặt lịch).
 *
 * ✅ ĐANG DÙNG THẬT: BookingPage.jsx import dưới tên BookingShowroomMap và render khi tab = 'map'.
 * (BookingPage.jsx còn một bản ShowroomMap cũ ở dòng ~446 nhưng bản đó KHÔNG được render nữa.)
 *
 * Bố cục: danh sách showroom bên trái · bản đồ bên phải · thẻ xem trước + nút "Xem lịch" nổi dưới.
 *
 * Bản đồ dùng gì:
 * - Thư viện Leaflet 1.9.4 tải TỪ CDN unpkg.com lúc chạy (không nằm trong package.json)
 *   → mất mạng thì bản đồ không hiện, dù phần còn lại của web vẫn chạy.
 * - Ô bản đồ (tile) lấy từ Google Maps. Chưa có API key nên chưa dùng được cho production.
 * - LƯU Ý: package.json có cài mapbox-gl nhưng file này KHÔNG dùng tới.
 * - Marker showroom là logo VinFast, marker vị trí người dùng là chấm tròn — cả hai vẽ bằng
 *   L.divIcon với class .leaflet-showroom-marker / .leaflet-user-marker (style ở cuối index.css).
 *
 * Khoảng cách "km" chỉ hiện khi backend trả về, không tự bịa số 0.
 * Sửa ở đây khi: đổi bố cục danh sách/bản đồ, đổi icon marker, đổi mức zoom (đang 11 và 14).
 */
import { useEffect, useRef, useState } from 'react'
import { Crosshair, Minus, Plus } from '@phosphor-icons/react'
import { commonMedia } from '../../media/assets'

const vinfastLogo = commonMedia.vinfastLogo
const distanceFormatter = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1 })

const formatDistance = (distance) => {
  if (distance === null || distance === undefined || distance === '') return ''
  const value = Number(distance)
  return Number.isFinite(value) ? distanceFormatter.format(value) : ''
}

export function ShowroomMap({ car, showrooms, selectedId, onSelect, onConfirm, userLocation, searchedLocation, disabled = false }) {
  const mapContainerRef = useRef(null)
  const mapRef = useRef(null)
  const markersRef = useRef([])
  const userMarkerRef = useRef(null)
  const searchedMarkerRef = useRef(null)
  const [leafletLoaded, setLeafletLoaded] = useState(false)
  const selected = showrooms.find((showroom) => showroom.id === selectedId) || null
  const hasLocation = Boolean(userLocation || searchedLocation)

  useEffect(() => {
    if (window.L) { setLeafletLoaded(true); return }
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    const script = document.createElement('script')
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
    script.async = true
    script.onload = () => setLeafletLoaded(true)
    document.body.appendChild(script)
  }, [])

  useEffect(() => {
    if (!leafletLoaded || !mapContainerRef.current) return
    const initialCenter = selected
      ? [selected.latitude, selected.longitude]
      : searchedLocation
        ? [searchedLocation.latitude, searchedLocation.longitude]
        : userLocation
          ? [userLocation.latitude, userLocation.longitude]
          : [21.028511, 105.804817]
    const map = window.L.map(mapContainerRef.current, { zoomControl: false }).setView(initialCenter, selected ? 14 : 11)
    window.L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', { attribution: '&copy; Google Maps' }).addTo(map)
    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [leafletLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !leafletLoaded) return
    const L = window.L
    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = showrooms.map((showroom) => {
      const active = selectedId === showroom.id ? ' is-active' : ''
      const icon = L.divIcon({ html: `<div class="leaflet-showroom-marker${active}"><img src="${vinfastLogo}" alt="VinFast" /></div>`, className: '', iconSize: [32, 32], iconAnchor: [16, 16], popupAnchor: [0, -16] })
      const marker = L.marker([showroom.latitude, showroom.longitude], { icon }).bindPopup(`<strong>${showroom.name}</strong><br/><small>${showroom.address}</small>`).addTo(map)
      marker.on('click', () => { if (!disabled) onSelect(showroom.id) })
      return marker
    })
  }, [showrooms, selectedId, onSelect, leafletLoaded, disabled])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !userLocation || !leafletLoaded) return
    userMarkerRef.current?.remove()
    const icon = window.L.divIcon({ html: '<div class="leaflet-user-marker"></div>', className: '', iconSize: [18, 18], iconAnchor: [9, 9] })
    userMarkerRef.current = window.L.marker([userLocation.latitude, userLocation.longitude], { icon }).addTo(map)
  }, [userLocation, leafletLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !leafletLoaded) return
    if (!searchedLocation) {
      searchedMarkerRef.current?.remove()
      searchedMarkerRef.current = null
      return
    }
    searchedMarkerRef.current?.remove()
    const icon = window.L.divIcon({
      html: '<div class="leaflet-searched-marker" style="background:#0C64E6;width:18px;height:18px;border-radius:50%;border:2px solid #ffffff;box-shadow:0 0 12px rgba(12,100,230,0.95), 0 0 20px rgba(12,100,230,0.5);"></div>',
      className: '',
      iconSize: [18, 18],
      iconAnchor: [9, 9],
    })
    searchedMarkerRef.current = window.L.marker([searchedLocation.latitude, searchedLocation.longitude], { icon }).bindPopup('<strong>Vị trí tìm kiếm</strong>').addTo(map)
  }, [searchedLocation, leafletLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !leafletLoaded || selected) return

    const targetPoints = []
    if (userLocation && Number.isFinite(userLocation.latitude) && Number.isFinite(userLocation.longitude)) {
      targetPoints.push([userLocation.latitude, userLocation.longitude])
    }
    if (searchedLocation && Number.isFinite(searchedLocation.latitude) && Number.isFinite(searchedLocation.longitude)) {
      targetPoints.push([searchedLocation.latitude, searchedLocation.longitude])
    }

    const nearbyShowroomPoints = showrooms
      .filter((showroom) => Number.isFinite(showroom.latitude) && Number.isFinite(showroom.longitude))
      .slice(0, 5)
      .map((showroom) => [showroom.latitude, showroom.longitude])

    const points = [...targetPoints, ...nearbyShowroomPoints]

    if (points.length === 1) {
      map.setView(points[0], 13, { animate: true })
    } else if (points.length > 1) {
      map.fitBounds(points, { padding: [50, 50], maxZoom: 13, animate: true })
    }
  }, [showrooms, userLocation, searchedLocation, selected, leafletLoaded])

  useEffect(() => {
    if (mapRef.current && selected && leafletLoaded) mapRef.current.setView([selected.latitude, selected.longitude], 14, { animate: true, duration: 1 })
  }, [selectedId, leafletLoaded])

  const centerUser = () => userLocation && mapRef.current?.setView([userLocation.latitude, userLocation.longitude], 14, { animate: true })

  return (
    <section className="studio-map studio-map--familiar" aria-label="Bản đồ showroom phù hợp">
      <aside className="studio-map__list">
        <div className="studio-map__intro" aria-live="polite">
          <strong><span className="studio-map__available-count">{showrooms.length}</span> showroom còn lịch cho {car.name}</strong>
          <small>{hasLocation ? 'Sắp xếp theo khoảng cách từ vị trí bạn cung cấp.' : 'Đang hiển thị theo lịch trống phù hợp.'}</small>
        </div>
        {showrooms.map((showroom, index) => (
          <button type="button" key={showroom.id} className={selectedId === showroom.id ? 'is-active' : ''} onClick={() => onSelect(showroom.id)} disabled={disabled}>
            <span className="studio-map__rank">{String(index + 1).padStart(2, '0')}</span>
            <span className="studio-map__showroom-copy">
              <strong>{showroom.name}</strong>
              <small>{showroom.address}</small>
              {showroom.available_slot_count ? <small>Còn {showroom.available_slot_count} lịch trống</small> : null}
            </span>
            {hasLocation && formatDistance(showroom.distance) && <em>{formatDistance(showroom.distance)} km</em>}
          </button>
        ))}
      </aside>
      <div className="studio-map__canvas">
        <div ref={mapContainerRef} className="studio-map__leaflet-container" />
        <div className="studio-map__controls" aria-label="Điều khiển bản đồ">
          <button type="button" onClick={() => mapRef.current?.zoomIn()} disabled={disabled} aria-label="Phóng to"><Plus size={17} weight="regular" /></button>
          <button type="button" onClick={() => mapRef.current?.zoomOut()} disabled={disabled} aria-label="Thu nhỏ"><Minus size={17} weight="regular" /></button>
          <button type="button" onClick={centerUser} disabled={disabled || !userLocation} aria-label="Vị trí của tôi"><Crosshair size={17} weight="regular" /></button>
        </div>
        {selected && <div className="studio-map__preview"><span><strong>{selected.name}</strong><small>{selected.address}{selected.phone ? ` · SĐT: ${selected.phone}` : ''}{hasLocation && formatDistance(selected.distance) ? ` · Cách bạn ${formatDistance(selected.distance)} km` : ''}</small></span><button type="button" onClick={() => onConfirm(selected)} disabled={disabled} className="studio-map__preview-confirm">Xem lịch</button></div>}
      </div>
    </section>
  )
}
