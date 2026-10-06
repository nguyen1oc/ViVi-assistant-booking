// Giá niêm yết tham chiếu từ resources/research/vinfast-gia-va-van-phong.md.
// Chỉ khai báo các mẫu đã có giá trong tài liệu; mẫu còn lại giữ dữ liệu catalogue hiện có.
const VEHICLE_PRICES = {
  vf3: { from: '285.000.000 VNĐ', variants: [{ name: 'Eco', price: '285.000.000 VNĐ' }, { name: 'Plus', price: '296.000.000 VNĐ' }] },
  vf5: { from: '496.000.000 VNĐ', variants: [{ name: '', price: '496.000.000 VNĐ' }] },
  vf6: { from: '646.000.000 VNĐ', variants: [{ name: 'Eco', price: '646.000.000 VNĐ' }, { name: 'Plus', price: '699.000.000 VNĐ' }] },
  vf7: { from: '740.000.000 VNĐ', variants: [{ name: 'Eco', price: '740.000.000 VNĐ' }, { name: 'Plus', price: '830.000.000 VNĐ' }, { name: 'Plus', detail: 'Trần kính toàn cảnh', price: '850.000.000 VNĐ' }] },
  'vf-mpv-7': { from: '750.000.000 VNĐ', variants: [{ name: '', price: '750.000.000 VNĐ' }] },
  vf8: { from: '898.000.000 VNĐ', variants: [{ name: 'Eco', price: '898.000.000 VNĐ' }, { name: 'Plus', price: '1.079.000.000 VNĐ' }] },
  vf9: { from: '1.348.000.000 VNĐ', variants: [{ name: 'Eco', price: '1.348.000.000 VNĐ' }, { name: 'Plus', price: '1.529.000.000 VNĐ' }] },
  'minio-green': { from: '188.000.000 VNĐ', variants: [{ name: '', price: '188.000.000 VNĐ' }] },
  'limo-green': { from: '699.000.000 VNĐ', variants: [{ name: '', price: '699.000.000 VNĐ' }] },
  'ec-van': { from: '268.000.000 VNĐ', variants: [{ name: '', price: '268.000.000 VNĐ' }] },
}

export const vehiclePrice = (vehicleId) => VEHICLE_PRICES[vehicleId] || null
