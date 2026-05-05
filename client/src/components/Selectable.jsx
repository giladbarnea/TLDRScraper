import { Check } from 'lucide-react'
import { useLongPress } from '../hooks/useLongPress'
import { interactionActions, useIsSelected } from '../store/articleStore'

function Selectable({ id, descendantIds = [], disabled = false, children }) {
  const isParent = descendantIds.length > 0
  const selected = useIsSelected(id)

  const handleLongPress = () => {
    if (isParent) interactionActions.containerLongPress(id, descendantIds)
    else interactionActions.itemLongPress(id)
  }

  const { handlers } = useLongPress(handleLongPress, { disabled })

  return (
    <div
      onPointerDown={(e) => { e.stopPropagation(); handlers.onPointerDown(e) }}
      onPointerMove={handlers.onPointerMove}
      onPointerUp={handlers.onPointerUp}
      onPointerCancel={handlers.onPointerCancel}
      data-selectable
      className="relative"
      style={{ touchAction: 'pan-y' }}
    >
      <div>
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
