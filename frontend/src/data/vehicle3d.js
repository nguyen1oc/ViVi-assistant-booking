/**
 * data/vehicle3d.js — Cấu hình model 3D cho trang chi tiết xe, trang trạm sạc và cinematic đặt lịch.
 *
 * ĐƯỜNG DẪN FILE — ĐỪNG TRỎ NGƯỢC RA `Ảnh xe vinfast/`
 * Ba file .glb nằm ở `src/media/local/models/` và ĐƯỢC GIT THEO DÕI. Trước đây chúng được
 * import thẳng từ `../../Ảnh xe vinfast/` — thư mục đó nặng 145 MB nên bị gitignore, khiến
 * mọi máy vừa clone repo về đều BUILD HỎNG với lỗi:
 *   Could not resolve "../../Ảnh xe vinfast/Trạm sạc/....glb?url" from "src/data/vehicle3d.js"
 * Nếu cần thêm model mới, nén rồi bỏ vào `src/media/local/models/`, đừng trỏ ra kho gốc.
 *
 * NÉN BẰNG DRACO, KHÔNG DÙNG MESHOPT
 * File gốc 145 MB đã được nén còn 3,0 MB bằng:
 *   npx @gltf-transform/cli optimize <gốc> <đích> --compress draco --texture-compress webp --texture-size 1024
 * Đã thử meshopt trước (nhỏ hơn nữa) nhưng model-viewer 4.3.1 KHÔNG giải mã được, báo lỗi
 * "Cannot read properties of undefined (reading 'scene')". Draco thì tải bình thường.
 * Đánh đổi: bộ giải mã Draco được model-viewer tải từ gstatic.com lúc chạy, nên xem 3D cần mạng.
 *
 * Bản gốc chưa nén vẫn nằm ở `frontend/Ảnh xe vinfast/` trên máy chủ dự án (không vào git).
 *
 * Góc camera và nhịp chuyển động do frontend sở hữu. Backend về sau chỉ cần trả
 * model3dUrl/model3dPreset đã được whitelist, không trả CSS hoặc JavaScript.
 */
import vf3ModelUrl from '../media/local/models/vf3.glb?url'
import vf9ModelUrl from '../media/local/models/vf9.glb?url'
import chargingStationModelUrl from '../media/local/models/charging-station.glb?url'

export const vehicle3dModels = {
  vf3: {
    src: vf3ModelUrl,
    orbit: '32deg 80deg 78%',
    // Đã kiểm tra trực tiếp trên GLB: 0° đầu xe, -90° hông (mũi hướng
    // theo chiều chạy sang phải), 180° cốp/đuôi xe.
    sideOrbit: '-90deg 76deg 106%',
    rearOrbit: '180deg 76deg 105%',
    fieldOfView: '28deg',
    credit: {
      author: 'Hoàng Huy',
      source: 'https://sketchfab.com/3d-models/vinfast-vf3-plus-2026-aa87e1cd1fdd42ae92e5a397e3d5b125',
      license: 'CC BY 4.0',
    },
  },
  vf9: {
    src: vf9ModelUrl,
    // VF9 dùng cùng hướng camera đã kiểm tra trực tiếp như VF3: 0° đầu xe,
    // -90° hông (mũi hướng sang phải), 180° cốp/đuôi xe.
    orbit: '-55deg 80deg 76%',
    sideOrbit: '-90deg 77deg 108%',
    rearOrbit: '180deg 77deg 105%',
    fieldOfView: '27deg',
    // Chỉ đổi vật liệu sơn thân; đèn hậu đỏ, kính và chrome vẫn giữ nguyên.
    paint: {
      // Sau bước Draco/texture palette, `Car Paint.002` trở thành tên mesh;
      // material thật mà model-viewer expose là PaletteMaterial001.
      materialName: 'PaletteMaterial001',
      removeBaseColorTexture: true,
      baseColor: [0.012, 0.014, 0.018, 1],
      metallicFactor: 0.9,
      roughnessFactor: 0.3,
    },
    credit: {
      author: 'Giang Trần',
      source: 'https://sketchfab.com/3d-models/vinfast-vf9-model-no-interior-cac6cb95b9084d0abee37dccb46fa10b',
      license: 'CC BY 4.0',
    },
  },
}

export const getVehicle3dModel = (vehicleId) => vehicle3dModels[vehicleId] || null

export const chargingStation3dModel = {
  src: chargingStationModelUrl,
  // GLB này có tâm hình học lệch lên trên vì chứa cả mái và nền trạm. Camera
  // target đã được đo trực tiếp trong model-viewer để toàn bộ cụm nằm giữa stage.
  orbit: '30deg 67deg 360%',
  sideOrbit: '30deg 67deg 360%',
  cameraTarget: '7.112m -4.8m -4.25m',
  fieldOfView: '38deg',
  exposure: '0.4',
  shadowIntensity: '1.8',
  environmentImage: 'neutral',
  credit: {
    author: 'Kho media VinFast P-053',
    license: 'Asset do dự án cung cấp',
  },
}
