/**
 * scripts/build-media-index.mjs — Sinh trang tra cứu ảnh frontend/media-index.html.
 *
 * Chạy:  npm run media:index      (hoặc: node scripts/build-media-index.mjs)
 * Rồi mở frontend/media-index.html bằng trình duyệt để XEM toàn bộ kho ảnh/video/model 3D,
 * nhóm theo mẫu xe, kèm tên file và dòng code hoặc đường dẫn để copy.
 *
 * Script chỉ ĐỌC thư mục ảnh và GHI ra một file HTML. Không sửa, không di chuyển ảnh nào.
 */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { vehicleMediaMap, sharedMediaMap, showcaseMediaMap } from '../src/media/vehicle-media-map.js'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND = path.resolve(HERE, '..')
const LOCAL = path.join(FRONTEND, 'src/media/local')
const OUT = path.join(FRONTEND, 'media-index.html')

const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.webp', '.svg'])
const VIDEO_EXT = new Set(['.mp4', '.mov'])
const MODEL_EXT = new Set(['.glb', '.gltf', '.fbx', '.obj', '.usdz'])

const esc = (value) => String(value).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
const kb = (bytes) => (bytes > 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`)
// Thư mục có dấu cách ("Dịch vụ_ EC Van") và tên file tiếng Việt phải mã hoá thì file:// mới mở được.
const srcUrl = (relPath) => encodeURI(relPath.split(path.sep).join('/'))
// macOS lưu tên file dạng NFD, chuỗi trong sổ tra cứu là NFC — so sánh phải quy về cùng một dạng.
const nfc = (value) => String(value).normalize('NFC')
// Thư mục nguồn trên macOS có thể ở Unicode NFD; dò bằng NFC để không phụ thuộc máy.
const ARCHIVE_DIR_NAME = fs.readdirSync(FRONTEND).find((name) => nfc(name) === 'Ảnh xe vinfast')
const ARCHIVE = ARCHIVE_DIR_NAME ? path.join(FRONTEND, ARCHIVE_DIR_NAME) : null

const listFiles = (dir) => {
  const full = path.join(LOCAL, dir)
  if (!fs.existsSync(full)) return []
  return fs.readdirSync(full)
    .filter((name) => !name.startsWith('.'))
    .map((name) => ({ name, abs: path.join(full, name) }))
    .filter((f) => fs.statSync(f.abs).isFile())
    .map((f) => ({
      ...f,
      rel: path.relative(FRONTEND, f.abs),
      ext: path.extname(f.name).toLowerCase(),
      size: fs.statSync(f.abs).size,
    }))
    .sort((a, b) => a.name.localeCompare(b.name, 'vi'))
}

/** Liệt kê đệ quy asset nguồn như GLB/GLTF vốn nằm sâu trong kho người dùng. */
const listTreeFiles = (root) => {
  if (!root || !fs.existsSync(root)) return []
  const files = []
  const walk = (dir) => {
    for (const name of fs.readdirSync(dir)) {
      if (name.startsWith('.')) continue
      const abs = path.join(dir, name)
      const stat = fs.statSync(abs)
      if (stat.isDirectory()) { walk(abs); continue }
      files.push({
        name,
        abs,
        rel: path.relative(FRONTEND, abs),
        ext: path.extname(name).toLowerCase(),
        size: stat.size,
      })
    }
  }
  walk(root)
  return files.sort((a, b) => a.rel.localeCompare(b.rel, 'vi'))
}

/** Tìm file trùng nội dung để cảnh báo ảnh thừa. */
const duplicateGroups = () => {
  const bySum = new Map()
  const walk = (dir) => {
    for (const name of fs.readdirSync(dir)) {
      if (name.startsWith('.')) continue
      const abs = path.join(dir, name)
      if (fs.statSync(abs).isDirectory()) { walk(abs); continue }
      const sum = crypto.createHash('sha1').update(fs.readFileSync(abs)).digest('hex')
      bySum.set(sum, [...(bySum.get(sum) || []), path.relative(LOCAL, abs)])
    }
  }
  walk(LOCAL)
  return [...bySum.values()].filter((group) => group.length > 1)
}

const thumbCell = (file, codeLine, badge = '') => {
  const isVideo = VIDEO_EXT.has(file.ext)
  const media = isVideo
    ? `<video src="${esc(srcUrl(file.rel))}" muted preload="metadata"></video>`
    : `<img loading="lazy" src="${esc(srcUrl(file.rel))}" alt="${esc(file.name)}">`
  return `<figure class="cell${badge ? ' is-key' : ''}">
    <div class="frame">${media}${badge ? `<span class="badge">${esc(badge)}</span>` : ''}</div>
    <figcaption>
      <strong title="${esc(file.name)}">${esc(file.name)}</strong>
      <small>${file.ext.slice(1)} · ${kb(file.size)}</small>
      ${codeLine ? `<button class="copy" data-code="${esc(codeLine)}">copy đường dẫn</button>` : ''}
    </figcaption>
  </figure>`
}

const modelCell = (file) => `<figure class="cell cell--model">
  <a class="frame model-frame" href="${esc(srcUrl(file.rel))}" title="Mở hoặc tải ${esc(file.name)}">
    <span class="model-glyph">3D</span><span class="badge">${esc(file.ext.slice(1).toUpperCase())}</span>
  </a>
  <figcaption>
    <strong title="${esc(file.name)}">${esc(file.name)}</strong>
    <small>${kb(file.size)} · ${esc(path.dirname(file.rel))}</small>
    <button class="copy" data-code="${esc(file.rel.split(path.sep).join('/'))}">copy đường dẫn</button>
  </figcaption>
</figure>`

const vehicleSection = ([id, entry]) => {
  const files = entry.folders.flatMap((folder) => listFiles(`vehicle-media/${folder}`))
  const keyName = nfc(path.basename(entry.thumbnail))
  const overrides = listFiles(`by-model/${id}`)

  const cells = files
    .filter((f) => IMAGE_EXT.has(f.ext) || VIDEO_EXT.has(f.ext))
    .map((f) => {
      const folder = path.basename(path.dirname(f.abs))
      const isKey = nfc(f.name) === keyName && nfc(entry.thumbnail).startsWith(nfc(folder))
      const isVideo = VIDEO_EXT.has(f.ext)
      const fn = isVideo ? 'vehicleVideo' : 'vehicleImage'
      return thumbCell(f, `${fn}('${folder}/${f.name}')`, isKey ? 'ẢNH CHÍNH' : '')
    })

  // Ảnh chính nằm trong common/ thì hiện riêng cho thấy nó không ở cùng thư mục xe.
  let commonCell = ''
  if (entry.thumbnail.startsWith('common/')) {
    const name = entry.thumbnail.slice('common/'.length)
    const file = listFiles('common').find((f) => nfc(f.name) === nfc(name))
    if (file) commonCell = thumbCell(file, `commonImage('${name}')`, 'ẢNH CHÍNH')
  }

  const overrideCells = overrides.length
    ? `<p class="override on">Đang ghi đè ${overrides.length} file trong <code>by-model/${esc(id)}/</code></p>
       <div class="grid">${overrides.map((f) => thumbCell(f, '', 'GHI ĐÈ')).join('')}</div>`
    : `<p class="override">Chưa ghi đè. Muốn đổi ảnh: bỏ file vào <code>src/media/local/by-model/${esc(id)}/studio.png</code></p>`

  return `<section id="${esc(id)}">
    <header class="vhead">
      <div>
        <h2>${esc(entry.name)} <code>${esc(id)}</code></h2>
        <p>${esc(entry.group)} · ${files.length + (commonCell ? 1 : 0)} file
           · thư mục: ${entry.folders.length ? entry.folders.map((f) => `<code>${esc(f)}</code>`).join(' + ') : '<em>không có thư mục riêng</em>'}</p>
      </div>
      <dl>
        <div><dt>Ảnh chính</dt><dd><code>${esc(entry.thumbnail)}</code></dd></div>
        ${entry.video ? `<div><dt>Video</dt><dd><code>${esc(entry.video)}</code></dd></div>` : ''}
        ${entry.brochure ? `<div><dt>Brochure</dt><dd>${esc(entry.brochure)}</dd></div>` : ''}
      </dl>
    </header>
    ${entry.note ? `<p class="note">⚠ ${esc(entry.note)}</p>` : ''}
    ${overrideCells}
    <div class="grid">${commonCell}${cells.join('')}</div>
  </section>`
}

const sharedSection = () => {
  const charging = listFiles('vehicle-media/Trạm sạc').map((f) => thumbCell(f, `vehicleAssetByName('Trạm sạc', '${f.name}')`))
  const common = listFiles('common').map((f) => thumbCell(f, `commonImage('${f.name}')`))
  const loose = listFiles('vehicle-media').map((f) => thumbCell(f, `vehicleImage('${f.name}')`))
  return `<section id="dung-chung">
    <header class="vhead"><div><h2>Ảnh dùng chung <code>không thuộc mẫu xe</code></h2>
      <p>Logo, ViVi, nhà máy, trạm sạc và các file nằm rời ở gốc thư mục.</p></div></header>
    <h3>Trạm sạc — dùng cho trang Pin &amp; trạm sạc</h3><div class="grid">${charging.join('')}</div>
    <h3>common/ — ảnh dùng chung</h3><div class="grid">${common.join('')}</div>
    <h3>Nằm rời ở gốc vehicle-media/</h3><div class="grid">${loose.join('')}</div>
  </section>`
}

const showcaseSection = () => {
  const blocks = Object.entries(showcaseMediaMap).map(([id, entry]) => {
    const files = listFiles(`showcase/${entry.folder}`)
    if (!files.length) return ''
    const cells = files.map((f) => thumbCell(f, `showcaseImage('${entry.folder}/${f.name}')`,
      f.name.startsWith('hero') ? 'ẢNH CHÍNH' : ''))

    // Ảnh gốc chưa tách nền: để cạnh bản cutout cho dễ đối chiếu khi cần xử lý lại.
    const raw = entry.originals ? listFiles(`originals/${entry.originals}`) : []
    const rawBlock = raw.length
      ? `<p class="override">Ảnh gốc chưa tách nền — <code>src/media/local/originals/${esc(entry.originals)}/</code>.
          Code không dùng tới, giữ để tách nền lại khi cần.</p>
         <div class="grid grid--raw">${raw.map((f) => thumbCell(f, '', 'ẢNH GỐC')).join('')}</div>`
      : ''

    return `<h3>${esc(entry.name)} — <code>${esc(id)}</code> · chưa mở lái thử</h3>
      <div class="grid">${cells.join('')}</div>${rawBlock}`
  }).join('')
  if (!blocks) return ''
  return `<section id="trung-bay"><header class="vhead"><div>
    <h2>Xe trưng bày <code>đã tách nền</code></h2>
    <p>Lạc Hồng — chỉ xuất hiện trên trang chủ, không nằm trong catalogue backend và không đặt lịch được.
       Ảnh dùng thật nằm ở <code>src/media/local/showcase/</code>, ảnh gốc ở <code>local/originals/</code>.</p>
    </div></header>${blocks}</section>`
}

const modelsSection = () => {
  const models = listTreeFiles(ARCHIVE).filter((file) => MODEL_EXT.has(file.ext))
  if (!models.length) return ''
  return `<section id="model-3d"><header class="vhead"><div>
    <h2>Model 3D <code>${models.length} file</code></h2>
    <p>GLB/GLTF/FBX/OBJ/USDZ trong kho nguồn. Nhấn ô để mở hoặc tải file; nút bên dưới copy đường dẫn tương đối.</p>
  </div></header><div class="grid">${models.map(modelCell).join('')}</div></section>`
}

const warningsSection = () => {
  const items = []
  const banner = path.join(LOCAL, 'vehicle-media/Banner')
  if (fs.existsSync(banner)) {
    items.push('<code>vehicle-media/Banner</code> là ảnh WebP nhưng <strong>không có đuôi file</strong> nên Vite không quét được — đổi tên thành <code>Banner.webp</code> mới dùng được.')
  }
  for (const group of duplicateGroups()) {
    items.push(`Trùng nội dung: ${group.map((p) => `<code>${esc(p)}</code>`).join(' = ')}`)
  }
  return items.length
    ? `<section id="canh-bao"><header class="vhead"><div><h2>Cảnh báo</h2>
        <p>Máy tự dò khi sinh trang này.</p></div></header>
        <ul class="warn">${items.map((i) => `<li>${i}</li>`).join('')}</ul></section>`
    : ''
}

const entries = Object.entries(vehicleMediaMap)
const localMediaTotal = fs.readdirSync(LOCAL, { recursive: true }).filter((f) => IMAGE_EXT.has(path.extname(String(f)).toLowerCase()) || VIDEO_EXT.has(path.extname(String(f)).toLowerCase())).length
const modelTotal = listTreeFiles(ARCHIVE).filter((file) => MODEL_EXT.has(file.ext)).length
const total = localMediaTotal + modelTotal

const html = `<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kho ảnh VinFast — tra cứu theo mẫu xe</title>
<style>
  *{box-sizing:border-box} body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f6f6f4;color:#1b1d21}
  header.top{position:sticky;top:0;z-index:9;background:#fff;border-bottom:1px solid #e6e6e2;padding:18px 26px}
  header.top h1{margin:0 0 4px;font-size:1.15rem} header.top p{margin:0;color:#6a6f76;font-size:.85rem}
  nav{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
  nav a{font-size:.76rem;padding:5px 11px;border-radius:999px;background:#f0f0ed;color:#33383f;text-decoration:none;border:1px solid transparent}
  nav a:hover{border-color:#1464F4;color:#1464F4}
  main{padding:26px;max-width:1500px;margin:0 auto}
  section{background:#fff;border:1px solid #e6e6e2;border-radius:16px;padding:22px;margin-bottom:22px}
  .vhead{display:flex;flex-wrap:wrap;gap:18px;justify-content:space-between;align-items:flex-start;border:0;padding:0;position:static;background:none}
  h2{margin:0 0 4px;font-size:1.05rem} h2 code{font-size:.75rem;background:#eef3ff;color:#1464F4;padding:2px 8px;border-radius:6px;margin-left:6px}
  h3{margin:22px 0 10px;font-size:.82rem;text-transform:uppercase;letter-spacing:.06em;color:#6a6f76}
  .vhead p{margin:0;color:#6a6f76;font-size:.82rem}
  dl{margin:0;display:grid;gap:3px;font-size:.78rem;min-width:260px}
  dl div{display:flex;gap:8px} dt{color:#8a9099;min-width:74px} dd{margin:0}
  code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.76rem;background:#f2f2ef;padding:1px 5px;border-radius:4px}
  .note{margin:14px 0 0;padding:10px 13px;background:#fff8e6;border-left:3px solid #e0a83b;border-radius:6px;font-size:.82rem}
  .override{margin:14px 0 4px;font-size:.8rem;color:#6a6f76} .override.on{color:#1e9e4a;font-weight:600}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(158px,1fr));gap:14px;margin-top:14px}
  .cell{margin:0} .frame{position:relative;aspect-ratio:4/3;background:repeating-conic-gradient(#eee 0 25%,#fff 0 50%) 50%/16px 16px;border:1px solid #e6e6e2;border-radius:10px;overflow:hidden;display:flex;align-items:center;justify-content:center}
  .cell.is-key .frame{border-color:#1464F4;box-shadow:0 0 0 2px rgba(20,100,244,.18)}
  .grid--raw .frame{background:#f0f0ed;border-style:dashed}
  .grid--raw .badge{background:#6a6f76}
  .frame img,.frame video{max-width:100%;max-height:100%;object-fit:contain}
  .model-frame{text-decoration:none;background:radial-gradient(circle at 50% 35%,#27384f,#111820 68%);color:#fff}
  .model-glyph{font-size:2.2rem;font-weight:720;letter-spacing:-.08em;text-shadow:0 12px 32px rgba(52,132,255,.5)}
  .badge{position:absolute;top:6px;left:6px;font-size:.6rem;font-weight:700;letter-spacing:.04em;background:#1464F4;color:#fff;padding:3px 7px;border-radius:5px}
  figcaption{padding:7px 2px 0} figcaption strong{display:block;font-size:.73rem;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  figcaption small{color:#8a9099;font-size:.68rem}
  .copy{margin-top:5px;font-size:.66rem;padding:3px 7px;border-radius:5px;border:1px solid #dcdcd8;background:#fafaf8;cursor:pointer;color:#4a4f57}
  .copy:hover{border-color:#1464F4;color:#1464F4} .copy.done{background:#e8f7ee;border-color:#1e9e4a;color:#1e9e4a}
  ul.warn{margin:12px 0 0;padding-left:20px;font-size:.83rem} ul.warn li{margin-bottom:7px}
</style></head><body>
<header class="top">
  <h1>Kho ảnh VinFast — tra cứu theo mẫu xe</h1>
  <p>${localMediaTotal} file ảnh/video · ${modelTotal} model 3D · sinh tự động lúc ${new Date().toLocaleString('vi-VN')} · chạy lại bằng <code>npm run media:index</code></p>
  <nav>${entries.map(([id, e]) => `<a href="#${esc(id)}">${esc(e.name)}</a>`).join('')}<a href="#trung-bay">Trưng bày</a><a href="#dung-chung">Dùng chung</a><a href="#model-3d">Model 3D</a><a href="#canh-bao">Cảnh báo</a></nav>
</header>
<main>
${entries.map(vehicleSection).join('\n')}
${sharedSection()}
${showcaseSection()}
${modelsSection()}
${warningsSection()}
</main>
<script>
document.addEventListener('click', (event) => {
  const button = event.target.closest('.copy')
  if (!button) return
  navigator.clipboard.writeText(button.dataset.code)
  button.textContent = 'đã copy'
  button.classList.add('done')
  setTimeout(() => { button.textContent = 'copy đường dẫn'; button.classList.remove('done') }, 1400)
})
</script>
</body></html>`

fs.writeFileSync(OUT, html, 'utf-8')
console.log(`Đã sinh ${path.relative(FRONTEND, OUT)} — ${entries.length} mẫu xe, ${localMediaTotal} ảnh/video, ${modelTotal} model 3D.`)
