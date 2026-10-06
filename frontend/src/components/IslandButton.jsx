/**
 * components/IslandButton.jsx — Nút bo tròn có mũi tên, dùng lại khắp các trang marketing.
 *
 * Tự chọn đúng thẻ HTML theo props: có `to` → <Link> nội bộ · có `to` + `external` → thẻ <a>
 * mở tab mới · không có `to` → <button> thường (dùng cho hành động, không phải điều hướng).
 *
 * Props điều khiển giao diện:
 * - variant: 'dark' (mặc định) · 'light' · 'blue' · 'ghost-light' → ra class .island-button--<tên>.
 * - icon: 'right' (mũi tên ngang, mặc định) hoặc 'up' (mũi tên chéo lên, ý là mở trang khác).
 *
 * Sửa MÀU/BO GÓC/HIỆU ỨNG HOVER của nút: tìm .island-button trong index.css, không sửa ở file này.
 */
import { ArrowRight, ArrowUpRight } from '@phosphor-icons/react'
import { Link } from 'react-router-dom'

export function IslandButton({
  to,
  children,
  variant = 'dark',
  external = false,
  className = '',
  icon = 'right',
  ...props
}) {
  const content = (
    <>
      <span>{children}</span>
      <span className="island-button__icon" aria-hidden="true">
        {icon === 'up' ? (
          <ArrowUpRight size={16} weight="light" />
        ) : (
          <ArrowRight size={16} weight="light" />
        )}
      </span>
    </>
  )

  const classes = `island-button island-button--${variant} ${className}`.trim()

  if (to && !external) {
    return (
      <Link className={classes} to={to} {...props}>
        {content}
      </Link>
    )
  }

  if (to && external) {
    return (
      <a className={classes} href={to} target="_blank" rel="noreferrer" {...props}>
        {content}
      </a>
    )
  }

  return (
    <button className={classes} type="button" {...props}>
      {content}
    </button>
  )
}
