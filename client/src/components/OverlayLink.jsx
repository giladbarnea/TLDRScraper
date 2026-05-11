import { useCallback, useRef } from 'react'
import { useLongPress } from '../hooks/useLongPress'
import { createPointPositionReference } from '../lib/floatingPositionReference'
import { POINTER_MOVE_THRESHOLD_PX } from '../lib/interactionConstants'
import { useOverlayLinkMenu } from './OverlayLinkMenuContext'

function openUrlInNewTab(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

function OverlayLink({ href, title, children }) {
  const { openOverlayLinkMenu } = useOverlayLinkMenu()
  const startPointRef = useRef(null)
  const cancelledPressRef = useRef(false)
  const suppressNextClickRef = useRef(false)

  const openMenuAtPoint = useCallback((point) => {
    suppressNextClickRef.current = true
    openOverlayLinkMenu({
      href,
      positionReference: createPointPositionReference(point.x, point.y),
    })
  }, [href, openOverlayLinkMenu])

  const handleLongPress = useCallback(() => {
    if (!startPointRef.current) return
    openMenuAtPoint(startPointRef.current)
  }, [openMenuAtPoint])

  const { handlers } = useLongPress(handleLongPress, { disabled: !href })

  if (!href) return <span>{children}</span>

  function handlePointerDown(event) {
    event.stopPropagation()
    startPointRef.current = { x: event.clientX, y: event.clientY }
    cancelledPressRef.current = false
    suppressNextClickRef.current = false
    handlers.onPointerDown(event)
  }

  function handlePointerMove(event) {
    event.stopPropagation()
    handlers.onPointerMove(event)
    if (!startPointRef.current) return

    const deltaX = Math.abs(event.clientX - startPointRef.current.x)
    const deltaY = Math.abs(event.clientY - startPointRef.current.y)
    cancelledPressRef.current = deltaX > POINTER_MOVE_THRESHOLD_PX || deltaY > POINTER_MOVE_THRESHOLD_PX
  }

  function handlePointerEnd(event) {
    event.stopPropagation()
    handlers.onPointerUp(event)
    startPointRef.current = null
  }

  function handlePointerCancel(event) {
    event.stopPropagation()
    handlers.onPointerCancel(event)
    startPointRef.current = null
    cancelledPressRef.current = true
  }

  function handleClick(event) {
    event.preventDefault()
    event.stopPropagation()

    const shouldSuppressClick = suppressNextClickRef.current || cancelledPressRef.current
    suppressNextClickRef.current = false
    cancelledPressRef.current = false
    if (shouldSuppressClick) return

    openUrlInNewTab(href)
  }

  function handleContextMenu(event) {
    event.preventDefault()
    event.stopPropagation()
    openMenuAtPoint({ x: event.clientX, y: event.clientY })
  }

  return (
    <button
      type="button"
      title={title || href}
      onClick={handleClick}
      onContextMenu={handleContextMenu}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerCancel}
      className="inline select-none cursor-pointer border-0 bg-transparent p-0 text-brand-600 underline decoration-brand-300 underline-offset-2 transition-colors hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-400/40 focus:ring-offset-1 [font:inherit] [line-height:inherit]"
      style={{ touchAction: 'pan-y' }}
    >
      {children}
    </button>
  )
}

export default OverlayLink
