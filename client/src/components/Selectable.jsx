import { Check } from 'lucide-react'
import { useCallback } from 'react'
import { useSelection } from '../contexts/SelectionContext'
import { useLongPress } from '../hooks/useLongPress'

function Selectable({ id, disabled = false, children }) {
  const { isSelectMode, toggle, isSelected } = useSelection()
  const selected = isSelected(id)

  const longPress = useLongPress(() => toggle(id), { disabled })

  const handleClickCapture = useCallback((e) => {
    if (disabled) return

    if (longPress.isLongPressRef.current) {
      e.stopPropagation()
      e.preventDefault()
      return
    }

    if (isSelectMode) {
      e.stopPropagation()
      e.preventDefault()
      toggle(id)
    }
  }, [isSelectMode, toggle, id, longPress.isLongPressRef, disabled])

  const showSelection = selected && !disabled

  return (
    <div
      className="relative"
      onClickCapture={handleClickCapture}
      {...longPress}
    >
      <div className={showSelection ? 'ring-4 ring-slate-300 rounded-[20px]' : ''}>
        {children}
      </div>

      {showSelection && (
        <div className="absolute top-2 left-2 z-20 w-7 h-7 rounded-full bg-brand-500 flex items-center justify-center shadow-md animate-check-enter">
          <Check size={16} className="text-white" strokeWidth={3} />
        </div>
      )}
    </div>
  )
}

export default Selectable
