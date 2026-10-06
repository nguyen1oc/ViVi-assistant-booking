/**
 * media/vehicle-media-map.js — SỔ TRA CỨU ẢNH THEO MẪU XE. Nguồn sự thật duy nhất.
 *
 * File này trả lời câu hỏi: "Mẫu xe X đang dùng ảnh nào, nằm ở thư mục nào?"
 * Nó là dữ liệu thuần — KHÔNG import gì cả — nên vừa dùng được trong web (qua vehicles.js),
 * vừa đọc được bằng script Node (scripts/build-media-index.mjs).
 *
 * ⚠️ Cột `thumbnail` phải KHỚP với bảng VEHICLES trong backend/scripts/publish_site_media.py.
 *   Đó là file backend copy sang backend/data/media/vehicles/<mã xe>/ để làm ảnh thẻ xe.
 *   Sửa lệch một bên là ảnh trên web sai so với ảnh trong kho.
 *
 * `id` chính là mã xe backend trả về ở GET /api/v1/vehicles — không được đặt tên khác.
 *
 * Đường dẫn viết theo 2 gốc:
 *   'VF9/CE18.webp'            → src/media/local/vehicle-media/VF9/CE18.webp
 *   'common/vf9-studio.png'    → src/media/local/common/vf9-studio.png
 *
 * MUỐN ĐỔI ẢNH MỘT MẪU XE: đừng sửa file này. Bỏ ảnh mới vào
 *   src/media/local/by-model/<mã xe>/studio.png  (hoặc thumbnail / hero / video)
 * Code tự ưu tiên ảnh trong đó. Xem src/media/local/by-model/README.md.
 */

export const vehicleMediaMap = {
  vf3: {
    name: 'VF 3',
    group: 'Động cơ điện',
    folders: ['VF3'],
    thumbnail: 'VF3/xám.png',
    video: '',
    brochure: '',
    model3d: 'VF3/vinfast_vf3_plus_2026.glb',
    note: 'Chưa có brochure trong kho. Tên file trong thư mục vô nghĩa: 1..webp, 2..png, 3..jpg, 4..png.',
  },
  vf5: {
    name: 'VF 5',
    group: 'Động cơ điện',
    folders: ['VF5'],
    thumbnail: 'VF5/trắng.webp',
    video: '',
    brochure: 'VFVN_VF 5_Brochure Bản sửa 290126_1333PM.pdf',
    note: 'VF5/1..webp trùng byte với VF3/1..webp — một trong hai đặt nhầm thư mục.',
  },
  vf6: {
    name: 'VF 6',
    group: 'Động cơ điện',
    folders: ['VF6'],
    thumbnail: 'common/vf6-front-model-cutout.png',
    video: '',
    brochure: 'VF6_Brochure.pdf',
    note: 'Ảnh chính nằm ở common/, KHÔNG nằm trong thư mục VF6. common/ còn 2 bản khác: vf6-model-cutout.png và vf6-studio.webp.',
  },
  vf7: {
    name: 'VF 7',
    group: 'Động cơ điện',
    folders: ['VF7', 'VF7 FMP'],
    thumbnail: 'VF7/product-CE18.webp',
    video: '',
    brochure: 'VF7_Brochure.pdf',
    note: 'Thư mục "VF7 FMP" (5 file D_01…D_05) CHƯA XÁC NHẬN thuộc mẫu nào — cần chủ dự án xác nhận.',
  },
  'vf-mpv-7': {
    name: 'VF MPV 7',
    group: 'Động cơ điện',
    folders: [],
    thumbnail: 'common/vf-mpv-7-model-cutout.png',
    video: '',
    brochure: '',
    note: 'KHÔNG có thư mục ảnh riêng. Cả mẫu xe chỉ có đúng 1 ảnh nằm trong common/.',
  },
  vf8: {
    name: 'VF 8',
    group: 'Động cơ điện',
    folders: ['VF8'],
    thumbnail: 'VF8/product-CE18.webp',
    video: 'VF8/VF8.mp4',
    brochure: 'VF8Brochure.pdf',
    note: 'VF8/VF8.mp4 dùng chung cho cả vf8 và vf8-the-he-moi (hai bản trước trùng byte).',
  },
  'vf8-the-he-moi': {
    name: 'VF 8 Thế hệ mới',
    group: 'Động cơ điện',
    folders: ['VF8 All the new'],
    thumbnail: 'VF8 All the new/VF8PH-23.webp',
    // Dùng CHUNG file với vf8: hai bản trước trùng byte 100%, giữ hai bản chỉ tốn 10,2 MB
    // trong bundle. Vẫn là hai bản ghi riêng để sau này thay video riêng cho từng mẫu được.
    video: 'VF8/VF8.mp4',
    brochure: 'VF 8 The he moi All News_Brochure_final 20.05.pdf',
    note: 'Tên thư mục "VF8 All the new" không khớp mã xe vf8-the-he-moi — dễ tìm nhầm.',
  },
  vf9: {
    name: 'VF 9',
    group: 'Động cơ điện',
    folders: ['VF9'],
    thumbnail: 'common/vf9-studio.png',
    video: 'VF9/VF9.mp4',
    brochure: 'VF 9_ Brochure.pdf',
    model3d: 'VF9/vinfast_vf9_model_no_interior.glb',
    note: 'Ảnh chính nằm ở common/. VF9/VF9 model.webp trùng byte với about-us.png.webp ở gốc vehicle-media.',
  },
  'herio-green': {
    name: 'Herio Green',
    group: 'Dòng xe dịch vụ',
    folders: ['Dịch vụ_Herio Green'],
    thumbnail: 'Dịch vụ_Herio Green/trắng.png',
    video: '',
    brochure: 'Dịch vụ_Catalogue-VinFast-Herio-Green.pdf',
    note: '',
  },
  'minio-green': {
    name: 'Minio Green',
    group: 'Dòng xe dịch vụ',
    folders: ['Dịch vụ_MINIO Green'],
    thumbnail: 'Dịch vụ_MINIO Green/Minio.webp',
    video: '',
    brochure: 'Dịch vụ_Brochure Minio Green 090126.pdf',
    note: 'Có 5 bản copy y hệt của interior-gallery-right@2x.webp — dấu vết tải trùng, nên xoá 4 bản thừa.',
  },
  'nerio-green': {
    name: 'Nerio Green',
    group: 'Dòng xe dịch vụ',
    folders: ['Dịch vụ_Nerio Green'],
    thumbnail: 'common/nerio-green-studio.png',
    video: '',
    brochure: 'Dịch vụ_Catalogue-VinFast-Nerio-Green.pdf',
    note: 'Ảnh chính nằm ở common/, không nằm trong thư mục xe.',
  },
  'limo-green': {
    name: 'Limo Green',
    group: 'Dòng xe dịch vụ',
    folders: ['Dịch vụ_Limo Green'],
    thumbnail: 'common/limo-green-studio.webp',
    video: 'Dịch vụ_Limo Green/Limo Green_Spacious Interior.mp4',
    brochure: 'Dịch  vụ_Brochure Limo Green 090126.pdf',
    note: 'Ảnh catalogue gốc nằm ở common/. Bản dùng thật đã được thay bằng by-model/limo-green/studio.webp có alpha; video nội thất chỉ hiện ở trang chi tiết.',
  },
  'ec-van': {
    name: 'EC Van',
    group: 'Dòng xe dịch vụ',
    folders: ['Dịch vụ_ EC Van'],
    thumbnail: 'Dịch vụ_ EC Van/ecvan-jade.webp',
    video: '',
    brochure: 'Dịch vụ_brochure-ec-van-040726-e.pdf',
    note: 'Tên thư mục THỪA MỘT DẤU CÁCH sau "Dịch vụ_" — gõ tay rất dễ sai, luôn copy từ đây.',
  },
  ebus: {
    name: 'VinFast eBus',
    group: 'Dòng xe dịch vụ',
    folders: ['Dịch vụ_EBus'],
    thumbnail: 'Dịch vụ_EBus/ebus-img-01.webp',
    video: '',
    brochure: 'Dịch vụ_VinFast-eBus_Broschure_092025.pdf',
    note: 'Ảnh đường phố gốc chỉ dùng làm nguồn. Bản dùng thật là by-model/ebus/studio.webp đã tách alpha.',
  },
}

/**
 * XE TRƯNG BÀY — có mặt trên trang chủ nhưng KHÔNG nằm trong catalogue của backend.
 *
 * Lạc Hồng đang được VinFast truyền thông nhưng chưa mở bán và chưa cho lái thử, nên hai mẫu
 * dưới đây cố ý KHÔNG có trong `vehicleMediaMap`: không có mã xe backend, không vào được
 * luồng đặt lịch, không xuất hiện trong dải thẻ xe. `bookable: false` là bất biến của sản phẩm,
 * đừng bật lên khi backend chưa thực sự mở lái thử.
 *
 * Ảnh nằm ở src/media/local/showcase/<id>/ và đã tách nền sẵn (PNG có alpha thật).
 */
export const showcaseMediaMap = {
  'lac-hong-900lx': {
    name: 'Lạc Hồng 900 LX',
    bookable: false,
    folder: 'lac-hong-900lx',
    // Ảnh gốc chưa tách nền, giữ ở local/originals/ để sau này xử lý lại được.
    // Không code nào dùng tới, không nằm trong bundle. Xem local/originals/README.md.
    originals: 'lac-hong-900lx',
    hero: 'lac-hong-900lx/hero-v2.png',
    emerge: 'lac-hong-900lx/front-emerge-v2.png',
    context: 'lac-hong-900lx/origin-vietnam.jpg',
    // FALLBACK CANVAS: bộ v2 là cutout alpha sạch, thứ tự camera đi vòng quanh xe.
    // UI vẽ vào một canvas duy nhất và chỉ đổi góc khi người dùng kéo; không render gallery.
    // Khi media API có GLB/GLTF thật, ưu tiên model3dUrl theo contract BACKEND_HANDOFF.md.
    spin: [
      'lac-hong-900lx/spin-1-v2.png',
      'lac-hong-900lx/spin-5-v2.png',
      'lac-hong-900lx/spin-3-v2.png',
      'lac-hong-900lx/spin-4-v2.png',
      'lac-hong-900lx/spin-2-v2.png',
      //'lac-hong-900lx/spin-1-v2.png',
      // 'lac-hong-900lx/spin-3-v2.png',
      // 'lac-hong-900lx/spin-5-v2.png',
      // 'lac-hong-900lx/spin-4-v2.png',
      // 'lac-hong-900lx/spin-2-v2.png',
    ],
  },
  'lac-hong-900s': {
    name: 'Lạc Hồng 900S',
    bookable: false,
    folder: 'lac-hong-900s',
    // Không có ảnh xe rời: hai ảnh 900S đều cắt ra từ tấm infographic 1772×6319.
    originals: 'lac-hong-900s',
    hero: 'lac-hong-900s/hero-v2.png',
    emerge: '',
    spin: [],
  },
}

/**
 * Ảnh KHÔNG thuộc mẫu xe nào. Ghi ra đây để không ai phải đoán khi mở thư mục.
 */
export const sharedMediaMap = {
  'Trạm sạc': 'Ảnh trụ sạc và model GLB, dùng cho trang Pin & trạm sạc (data/ownership.js + components/Vehicle3DExperience.jsx).',
  'common/vinfast-logo.png': 'Logo trên bản đồ showroom.',
  'common/vivi-avatar.png': 'Ảnh đại diện ViVi cạnh mỗi tin nhắn.',
  'common/vivi-portrait-cutout.png': 'Chân dung ViVi cỡ lớn đã tách alpha, đặt trực tiếp trên nền trang chủ.',
  'common/vinfast-road-banner.webp': 'Ảnh xe trên đường ở trang chủ.',
  'common/after-sales-hero.webp': 'Ảnh đầu trang Hậu mãi.',
  'common/after-sales-consultation.webp': 'Ảnh tư vấn ở trang Hậu mãi.',
  'Vinfast-logo-new_NO_Tagline -2D-Horizontal black.png': 'Logo ngang trên header (components/Brand.jsx).',
  'Ảnh ViVi.jpeg': 'Ảnh ViVi nền trắng nguyên bản, chỉ giữ làm nguồn; giao diện dùng common/vivi-portrait-cutout.png.',
  'nha-may-vinfast.jpg': 'Toàn cảnh nhà máy, trang chủ.',
  'about-us.png.webp': 'Ảnh VF 9 ở mục giới thiệu trang chủ.',
  'Video chính.mp4': 'Video dây chuyền nhà máy, trang chủ.',
  'footprint-vf8.png.webp': 'Chưa thấy chỗ nào dùng.',
  'footprint-vf9.png.webp': 'Chưa thấy chỗ nào dùng.',
  Banner: 'HỎNG: là ảnh WebP nhưng KHÔNG có đuôi file nên Vite không quét được. Đổi tên thành Banner.webp mới dùng được.',
}

/** Danh sách slot được phép ghi đè trong by-model/<mã xe>/. */
export const OVERRIDABLE_SLOTS = ['thumbnail', 'studio', 'hero', 'video']
