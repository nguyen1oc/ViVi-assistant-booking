/**
 * scripts/apply-model-overrides.mjs — Đẩy ảnh ghi đè sang kho media của backend.
 *
 * Chạy:  npm run media:apply       (dev-local.sh tự gọi, thường không cần chạy tay)
 *
 * VÌ SAO CẦN BƯỚC NÀY
 * Ảnh thẻ xe trên web KHÔNG lấy từ bundle frontend mà lấy từ backend qua URL
 * /media/vehicles/<mã xe>/thumbnail.*. Nên file bỏ vào by-model/<mã xe>/thumbnail.png
 * phải được copy sang kho của backend thì mới thấy đổi.
 *
 * PHẠM VI: chỉ GHI vào backend/data/media/ — đây là dữ liệu sinh ra lúc chạy, đã nằm trong
 * .gitignore. Script KHÔNG đụng một dòng mã nguồn nào của backend.
 *
 * Ảnh marketing (trang chủ, trang chi tiết) không cần bước này — Vite nạp thẳng, F5 là thấy.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { vehicleMediaMap } from '../src/media/vehicle-media-map.js'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND = path.resolve(HERE, '..')
const BY_MODEL = path.join(FRONTEND, 'src/media/local/by-model')
const MEDIA_ROOT = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.resolve(FRONTEND, '../backend/data/media')

// Tên slot trong by-model/ -> tên file backend đang phục vụ.
const SLOT_TARGETS = {
  thumbnail: 'thumbnail',
  studio: 'studio',
  video: 'presentation',
}

if (!fs.existsSync(MEDIA_ROOT)) {
  console.log(`Bỏ qua: chưa có kho media của backend (${MEDIA_ROOT}). Chạy dev-local.sh trước.`)
  process.exit(0)
}

const findOverride = (vehicleId, slot) => {
  const dir = path.join(BY_MODEL, vehicleId)
  if (!fs.existsSync(dir)) return null
  const hit = fs.readdirSync(dir)
    .filter((name) => path.parse(name).name === slot && !name.startsWith('.'))
    .sort()[0]
  return hit ? path.join(dir, hit) : null
}

let applied = 0
const warnings = []

for (const vehicleId of Object.keys(vehicleMediaMap)) {
  const targetDir = path.join(MEDIA_ROOT, 'vehicles', vehicleId)

  for (const [slot, targetBase] of Object.entries(SLOT_TARGETS)) {
    const source = findOverride(vehicleId, slot)
    if (!source) continue

    // Backend đã chốt sẵn phần đuôi file trong URL của API, nên phải ghi đè lên
    // ĐÚNG tên file đang có, không được tự tạo tên mới.
    const existing = fs.existsSync(targetDir)
      ? fs.readdirSync(targetDir).find((name) => path.parse(name).name === targetBase)
      : null

    if (!existing) {
      warnings.push(`${vehicleId}/${slot}: backend chưa có file ${targetBase}.* để ghi đè — bỏ qua.`)
      continue
    }

    const sourceExt = path.extname(source).toLowerCase()
    const targetExt = path.extname(existing).toLowerCase()
    if (sourceExt !== targetExt) {
      warnings.push(
        `${vehicleId}/${slot}: file của anh là ${sourceExt} nhưng backend đang phục vụ ${targetExt}. `
        + `Đổi tên thành "${slot}${targetExt}" để trình duyệt hiển thị đúng.`,
      )
    }

    fs.copyFileSync(source, path.join(targetDir, existing))
    console.log(`  ghi đè  ${vehicleId}/${existing}  ←  by-model/${vehicleId}/${path.basename(source)}`)
    applied += 1
  }
}

console.log(applied ? `Đã áp dụng ${applied} ảnh ghi đè.` : 'Không có ảnh ghi đè nào trong by-model/.')
for (const warning of warnings) console.log(`  ⚠ ${warning}`)
