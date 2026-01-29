import { Check } from 'lucide-react'
import { useCallback } from 'react'
import { useSelection } from '../contexts/SelectionContext'
import { useLongPress } from '../hooks/useLongPress'

function Selectable({ id, descendantIds = [], disabled = false, children }) {
  const { isSelectMode, toggle, selectMany, isSelected } = useSelection()
  const selected = isSelected(id)

  const handleLongPress = useCallback(() => {
    if (descendantIds.length > 0) {
      selectMany([id, ...descendantIds])
    } else {
      toggle(id)
    }
  }, [id, descendantIds, selectMany, toggle])

  const longPress = useLongPress(handleLongPress, { disabled })

  const handleClick = useCallback((e) => {
    if (longPress.isLongPressRef.current) {
      e.stopPropagation()
      e.preventDefault()
      return
    }

    if (isSelectMode) {
      e.stopPropagation()
      e.preventDefault()
      if (descendantIds.length > 0) {
        selectMany([id, ...descendantIds])
      } else {
        toggle(id)
      }
    }
  }, [isSelectMode, id, descendantIds, selectMany, toggle, longPress.isLongPressRef])

  return (
    <div
      className="relative"
      onClickCapture={handleClick}
      {...longPress}
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
