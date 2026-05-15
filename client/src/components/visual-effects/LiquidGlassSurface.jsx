export default function LiquidGlassSurface({
  variant = 'solid',
  depth = 'compact',
  lens = 'subtle',
  className = '',
  children,
  ...props
}) {
  const surfaceClassName = ['liquid-glass-surface', className].filter(Boolean).join(' ')

  return (
    <div
      data-liquid-glass-variant={variant}
      data-liquid-glass-depth={depth}
      data-liquid-glass-lens={lens}
      className={surfaceClassName}
      {...props}
    >
      {children}
    </div>
  )
}
