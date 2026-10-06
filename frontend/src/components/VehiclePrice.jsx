export function VehiclePriceVariants({ variants, fallback, className = '' }) {
  if (!variants?.length) return fallback || 'Đang cập nhật'

  return (
    <span className={className}>
      {variants.map((variant) => (
        <span className={`${className}__row`} key={`${variant.name}-${variant.price}`}>
          {variant.name && (
            <span>
              {variant.name}
              {variant.detail && <> <span className={`${className}__detail`}>{variant.detail}</span></>}
            </span>
          )}
          <span>{variant.price}</span>
        </span>
      ))}
    </span>
  )
}
