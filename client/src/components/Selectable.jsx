import { Check } from 'lucide-react'
import { useCallback, useRef } from 'react'
import { useSelection } from '../contexts/SelectionContext'
import { useLongPress } from '../hooks/useLongPress'

function Selectable({ id, descendantIds = [], disabled = false, children }) {
  const { isSelectMode, toggle, selectMany, deselectMany, isSelected } = useSelection()
  const isParent = descendantIds.length > 0
  const allDescendantsSelected = isParent
    ? descendantIds.length > 0 && descendantIds.every((descendantId) => isSelected(descendantId))
    : false
  const selected = !isParent && isSelected(id)
  const wrapperRef = useRef(null)
  const activePressRef = useRef(false)

  const handleSelect = useCallback(() => {
    if (disabled) return
    if (isParent) {
      if (allDescendantsSelected) {
        deselectMany(descendantIds)
      } else {
        selectMany(descendantIds)
      }
      return
    }
    toggle(id)
  }, [disabled, isParent, allDescendantsSelected, deselectMany, selectMany, descendantIds, toggle, id])

  const longPress = useLongPress(handleSelect, { disabled })

  const isSelfEvent = useCallback((event) => {
    return event.target?.closest?.('[data-selectable]') === wrapperRef.current
  }, [])

  const handleClickCapture = useCallback((e) => {
    const closestSelectable = e.target.closest('[data-selectable]')
    if (closestSelectable !== wrapperRef.current) return

    if (longPress.isLongPressRef.current) {
      e.stopPropagation()
      e.preventDefault()
      return
    }

    if (isSelectMode && !isParent && !disabled) {
      e.stopPropagation()
      e.preventDefault()
      handleSelect()
    }
  }, [isSelectMode, isParent, disabled, handleSelect, longPress.isLongPressRef])

  const longPressHandlers = {
    onTouchStart: (e) => {
      if (!isSelfEvent(e)) return
      activePressRef.current = true
      longPress.handlers.onTouchStart(e)
    },
    onTouchMove: (e) => {
      if (!activePressRef.current) return
      longPress.handlers.onTouchMove(e)
    },
    onTouchEnd: (e) => {
      if (!activePressRef.current) return
      activePressRef.current = false
      longPress.handlers.onTouchEnd(e)
    },
    onMouseDown: (e) => {
      if (!isSelfEvent(e)) return
      activePressRef.current = true
      longPress.handlers.onMouseDown(e)
    },
    onMouseMove: (e) => {
      if (!activePressRef.current) return
      longPress.handlers.onMouseMove(e)
    },
    onMouseUp: (e) => {
      if (!activePressRef.current) return
      activePressRef.current = false
      longPress.handlers.onMouseUp(e)
    },
    onMouseLeave: (e) => {
      if (!activePressRef.current) return
      activePressRef.current = false
      longPress.handlers.onMouseLeave(e)
    },
  }

  return (
    <div
      ref={wrapperRef}
      data-selectable
      className="relative"
      onClickCapture={handleClickCapture}
      {...longPressHandlers}
    >
      <div className={selected ? 'ring-4 ring-slate-300 rounded-[20px]' : ''}>
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
