/**
 * VehicleColorConfigurator — section chọn màu dùng chung cho mọi trang model.
 *
 * FRONTEND/BACKEND CONTRACT:
 * - Bắt buộc: color.name, color.image, và MỘT trong hai cách mô tả màu:
 *     · color.hex     — mã màu phẳng (backend trả).
 *     · color.swatch  — URL ảnh chip màu chính hãng (bảng bù ở data/vehicle-colors.js).
 *   Ảnh chip tồn tại vì sơn kim loại không quy về một hex phẳng được; chính vinfast.vn cũng
 *   vẽ swatch bằng ảnh. Có `swatch` thì `hex` không còn bắt buộc.
 * - Tuỳ chọn: color.group, color.groupLabel để chia nhóm màu; color.secondaryHex
 *   (hoặc color.hexes) để vẽ swatch hai tông. Thiếu các field tuỳ chọn thì UI
 *   giữ một dải màu phẳng, không tự suy đoán hay tạo dữ liệu sản phẩm.
 * - vehicle.specs tiếp tục dùng schema { label, value }; field thiếu tự ẩn.
 *
 * State chọn màu được giữ cục bộ như ColorExplorer trước đây; mapping color -> image không đổi.
 * Section này KHÔNG còn CTA đặt lịch — xem lý do ở comment cạnh .color-explorer__palette.
 */
import { useState } from 'react'
import { SmartImage } from './SmartImage'

const GROUP_LABELS = {
  standard: 'Màu tiêu chuẩn',
  premium: 'Màu nâng cao',
  advanced: 'Màu nâng cao',
  special: 'Màu đặc biệt',
  'two-tone': 'Màu hai tông',
  other: 'Màu khác',
}

const publishedHexPattern = /^#[0-9a-f]{6}$/i

function getPublishedTones(color) {
  return (Array.isArray(color.hexes)
    ? color.hexes.filter(Boolean).slice(0, 2)
    : [color.hex, color.secondaryHex || color.hex2].filter(Boolean))
    .filter((tone) => publishedHexPattern.test(tone))
}

function getSwatchBackground(color) {
  const tones = getPublishedTones(color)

  if (tones.length > 1) {
    return `linear-gradient(135deg, ${tones[0]} 0 48%, ${tones[1]} 52% 100%)`
  }

  return tones[0]
}

/**
 * Một ô màu. Ưu tiên ảnh chip chính hãng nếu có, nếu không thì tô nền bằng hex
 * (một hoặc hai tông). Luôn là <span> để hai nhánh dùng chung y hệt bố cục và kích thước.
 */
function ColorSwatch({ color }) {
  if (color.swatch) {
    return (
      <span className="color-explorer__swatch-image" aria-hidden="true">
        <img src={color.swatch} alt="" loading="lazy" />
      </span>
    )
  }
  return <span style={{ background: getSwatchBackground(color) }} aria-hidden="true" />
}

function groupColors(colors) {
  const hasExplicitGroups = colors.some((color) => color.group)
  if (!hasExplicitGroups) return [{ key: 'all', label: '', colors }]

  return colors.reduce((groups, color) => {
    const key = color.group || 'other'
    let group = groups.find((item) => item.key === key)
    if (!group) {
      group = {
        key,
        label: color.groupLabel || GROUP_LABELS[key] || key,
        colors: [],
      }
      groups.push(group)
    }
    group.colors.push(color)
    return groups
  }, [])
}

export function VehicleColorConfigurator({ vehicle }) {
  const availableColors = (vehicle.colors || []).filter((color) => (
    color?.image && color?.name && (color?.swatch || publishedHexPattern.test(color?.hex || ''))
  ))
  const visibleSpecs = (vehicle.specs || []).filter((spec) => spec?.value && spec?.label).slice(0, 4)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const selected = availableColors[selectedIndex]
  const intro = vehicle.tagline

  if (!availableColors.length) {
    // TODO(BE): Publish named color media in the vehicle detail payload. Until
    // then this state must stay explicit rather than inventing swatches/images.
    return (
      <section id="colors" className="color-explorer color-explorer--empty" aria-labelledby={`color-title-${vehicle.id}`}>
        <div className="section-frame">
          <div className="color-explorer__empty">
            <p className="eyebrow">{vehicle.name} · Màu ngoại thất</p>
            <h2 id={`color-title-${vehicle.id}`}>Bảng màu của {vehicle.name} đang được cập nhật.</h2>
            {intro && <p>{intro}</p>}
            <span>Chưa có ảnh màu đã được công bố để hiển thị tại đây.</span>
          </div>
        </div>
      </section>
    )
  }

  const indexedColors = availableColors.map((color, index) => ({ ...color, sourceIndex: index }))
  const colorGroups = groupColors(indexedColors)

  return (
    <section id="colors" className="color-explorer" aria-labelledby={`color-title-${vehicle.id}`}>
      <div className="section-frame">
        <div className="color-explorer__stage">
          <div className="color-explorer__grid">
            <header className="color-explorer__copy">
              <p className="eyebrow">{vehicle.name} · Bảng màu ngoại thất</p>
              <h2 id={`color-title-${vehicle.id}`}>Màu ngoại thất của {vehicle.name}.</h2>
              {intro && <p>{intro}</p>}
            </header>

            {visibleSpecs.length > 0 && (
              <dl className="color-explorer__specs" aria-label={`Thông số nổi bật ${vehicle.name}`}>
                {visibleSpecs.map((spec, index) => (
                  <div className="color-explorer__spec" key={`${spec.label}-${spec.value}-${index}`}>
                    <dt>{spec.label}</dt>
                    <dd>{spec.value}</dd>
                  </div>
                ))}
              </dl>
            )}

            <div className="color-explorer__visual">
              <SmartImage
                key={selected.image}
                className="color-explorer__image"
                src={selected.image}
                alt={`${vehicle.name} màu ${selected.name}`}
              />
            </div>

            <div className="color-explorer__palette">
              <p className="color-explorer__name" aria-live="polite" aria-atomic="true">
                <span>Màu đang chọn</span>
                <strong>{selected.name}</strong>
              </p>

              <div className={`color-explorer__groups ${colorGroups.length > 1 ? 'has-multiple-groups' : ''}`}>
                {availableColors.length === 1 ? (
                  <div className="color-explorer__single-color" aria-label={`Màu ngoại thất ${selected.name}`}>
                    <ColorSwatch color={selected} />
                    <small>Một màu đang được công bố</small>
                  </div>
                ) : colorGroups.map((group) => (
                    <div className="color-explorer__group" key={group.key}>
                      {group.label && <p>{group.label}</p>}
                      <div className="color-explorer__swatches" role="group" aria-label={group.label || `Chọn màu ${vehicle.name}`}>
                        {group.colors.map((color) => {
                          const isSelected = selectedIndex === color.sourceIndex
                          return (
                            <button
                              key={`${color.name}-${color.sourceIndex}`}
                              className={isSelected ? 'is-active' : ''}
                              type="button"
                              aria-pressed={isSelected}
                              aria-label={`${color.name}${isSelected ? ', đang chọn' : ''}`}
                              title={color.name}
                              onClick={() => setSelectedIndex(color.sourceIndex)}
                            >
                              <ColorSwatch color={color} />
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ))}
              </div>

              {/* Nút "Đặt lịch lái thử" ở đây đã gỡ trong đợt dọn CTA: .detail-booking-dock
                  là position:fixed và hiện ở MỌI breakpoint (mobile còn kéo full-width ngay
                  dưới khối này), nên nó lặp lại đúng chữ và đúng /booking?car=<id> trong cùng
                  một khung nhìn. Hành động chính của section này là chọn màu. */}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
