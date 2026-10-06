/**
 * data/ownership.js — Ảnh và số liệu chính sách cho 2 trang Hậu mãi và Pin & trạm sạc.
 *
 * Nội dung được gõ lại từ brochure chính thức của VinFast, chưa lấy từ CMS.
 *
 * Chứa gì:
 * - ownershipMedia: bảng tra ảnh — hero 2 trang, ảnh tư vấn, 4 loại trụ sạc (250/150/60/30 kW),
 *   sạc treo tường, sạc di động, và 2 link PDF brochure (bảo hành, pin ô tô).
 * - highVoltageWarranty: bảng thời hạn bảo hành pin cao áp (10 năm/200.000 km · 8 năm/160.000 km
 *   · 7 năm/160.000 km) kèm danh sách mẫu xe áp dụng.
 * - chargingUnits: danh mục 4 trụ sạc với công suất, số cổng, dải điện áp, chuẩn IP, nhiệt độ.
 *
 * ⚠️ Hai mảng cuối hiện đã bị backend GHI ĐÈ khi API trả dữ liệu:
 *   AfterSalesPage dùng content.warrantyTables, ChargingPage dùng content.chargingUnits.
 *   Sửa số liệu ở file này sẽ KHÔNG đổi trên web nếu backend đang trả về dữ liệu tương ứng.
 *   Phần ảnh (ownershipMedia) thì vẫn dùng thật.
 */
import { brochureByKeyword, commonMedia, vehicleAssetByName } from '../media/assets'

const chargingImage = (fileName) => vehicleAssetByName('Trạm sạc', fileName)

// TODO [BACKEND/CMS]: Replace the brochure-backed fixtures below with
// GET /api/v1/content/ownership?locale=vi-VN. The API should return a source
// revision/effectiveAt for every policy block so legal copy can be audited.
export const ownershipMedia = {
  afterSalesHero: commonMedia.afterSalesHero,
  afterSalesConsultation: commonMedia.afterSalesConsultation,
  afterSalesBrochure: brochureByKeyword('bảo hành'),
  chargingBrochure: brochureByKeyword('pin ô tô'),
  chargingStationDay: chargingImage('pin-tramsac-5_1660273699.png.webp'),
  chargingStationNight: chargingImage('pin-tramsac-6_1660273722.png.webp'),
  // Product cutouts v2: 1.5K PNG có alpha thật. Giữ file brochure cũ làm
  // nguồn tham chiếu, nhưng không dùng trực tiếp vì chỉ cao 180 px và có nền.
  charger250: chargingImage('charger-250-cutout-v2.png'),
  charger150: chargingImage('charger-150-cutout-v2.png'),
  charger60: chargingImage('charger-60-cutout-v2.png'),
  charger30: chargingImage('charger-30-cutout-v2.png'),
  wallCharger: chargingImage('pin-tramsac-11_1660273822.png.webp'),
  portableCharger: chargingImage('pin-tramsac-12_1660273840.png.webp'),
  portableChargerAlt: chargingImage('pin-tramsac-13_1660273860.png.webp'),
  availableIndicator: chargingImage('pin-tramsac-14_1660273636.png.webp'),
}

export const highVoltageWarranty = [
  {
    term: '10 năm',
    distance: '200.000 km',
    models: 'VF 8, VF 9, Lạc Hồng 900 LX',
  },
  {
    term: '8 năm',
    distance: '160.000 km',
    models: 'VF 3, VF 5, VF 6, VF 7, VF Minio Green, VF Herio Green, VF MPV7, VF e34, VF Nerio Green, VF Limo Green, VF 8 The All New',
  },
  {
    term: '7 năm',
    distance: '160.000 km',
    models: 'VF EC Van',
  },
]
export const chargingUnits = [
  {
    power: '250 kW',
    name: 'Sạc siêu nhanh DC',
    image: ownershipMedia.charger250,
    facts: ['Tủ đứng', '1 cổng / trụ', '200–1.000 VDC', 'IP54 · −30°C đến 55°C'],
  },
  {
    power: '150 kW',
    name: 'Sạc siêu nhanh DC',
    image: ownershipMedia.charger150,
    facts: ['Tủ đứng', '2 cổng / trụ', '200–1.000 VDC', 'IP54'],
  },
  {
    power: '60 kW',
    name: 'Sạc nhanh DC',
    image: ownershipMedia.charger60,
    facts: ['Tủ đứng', '2 cổng / trụ', '200–1.000 VDC', 'IP54'],
  },
  {
    power: '30 kW',
    name: 'Sạc nhanh DC',
    image: ownershipMedia.charger30,
    facts: ['Treo tường hoặc tủ đứng', '1 cổng / trụ', 'CAN Protocol', 'IP54'],
  },
]
