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

  const handleClickCapture = useCallback((e) => {
    const closestSelectable = e.target.closest('[data-selectable]')
    if (closestSelectable !== wrapperRef.current) return
    if (e.target.closest('[data-fold-toggle]')) return

    if (longPress.isLongPressRef.current) {
      e.stopPropagation()
      e.preventDefault()
      return
    }

    if (isSelectMode) {
      e.stopPropagation()
      e.preventDefault()
      handleSelect()
    }
  }, [isSelectMode, handleSelect, longPress.isLongPressRef])

  return (
    <div
      ref={wrapperRef}
      data-selectable
      className="relative"
      onClickCapture={handleClickCapture}
      {...longPress.handlers}
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
