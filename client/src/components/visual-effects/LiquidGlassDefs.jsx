export default function LiquidGlassDefs() {
  return (
    <svg width="0" height="0" aria-hidden="true" style={{ position: 'absolute' }}>
      <filter id="liquid-glass-lens-subtle" x="-10%" y="-10%" width="120%" height="120%" colorInterpolationFilters="linearRGB">
        <feDisplacementMap in="SourceGraphic" in2="SourceGraphic" scale="40" xChannelSelector="R" yChannelSelector="B" />
      </filter>
    </svg>
  )
}
