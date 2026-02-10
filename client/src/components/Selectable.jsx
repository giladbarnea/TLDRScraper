import { Check } from 'lucide-react'
import { useCallback, useMemo, useRef } from 'react'
import { useInteraction } from '../contexts/InteractionContext'
import { useLongPress } from '../hooks/useLongPress'

function Selectable({ id, descendantIds = [], disabled = false, children }) {
  const {
    isSelected,
    itemLongPress,
    containerLongPress,
  } = useInteraction()
  const isParent = descendantIds.length > 0
  const selected = useMemo(() => {
    return !isParent && isSelected(id)
  }, [isParent, isSelected, id])
  const wrapperRef = useRef(null)

  const onLongPress = useCallback(() => {
    if (disabled) return
    if (isParent) {
      containerLongPress(id, descendantIds)
      return
    }
    itemLongPress(id)
  }, [disabled, isParent, containerLongPress, id, descendantIds, itemLongPress])

  const longPress = useLongPress(onLongPress, { disabled })

  const isSelfEvent = useCallback((event) => {
    return event.target?.closest?.('[data-selectable]') === wrapperRef.current
  }, [])

  const handlePointerDown = useCallback((event) => {
    if (!isSelfEvent(event)) return
    longPress.handlers.onPointerDown(event)
  }, [isSelfEvent, longPress.handlers])

  const handlePointerMove = useCallback((event) => {
    longPress.handlers.onPointerMove(event)
  }, [longPress.handlers])

  const handlePointerUp = useCallback((event) => {
    longPress.handlers.onPointerUp(event)
  }, [longPress.handlers])

  const handlePointerCancel = useCallback((event) => {
    longPress.handlers.onPointerCancel(event)
  }, [longPress.handlers])

  return (
    <div
      ref={wrapperRef}
      data-selectable
      className="relative"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      onContextMenu={(event) => {
        if (isSelfEvent(event)) event.preventDefault()
      }}
      style={{ touchAction: 'pan-y' }}
    >
      <div className={selected ? 'ring-4 ring-slate-300 rounded-xl' : ''}>
        {children}
      </div>

      {selected && (
        <div className="absolute top-2 left-2 z-20 w-7 h-7 rounded-full bg-brand-500 flex items-center justify-center shadow-md animate-check-enter">
          <Check size={16} className="text-white" strokeWidth={3} />
        </div>
      )}
    </div>
  )
}

export default Selectable
