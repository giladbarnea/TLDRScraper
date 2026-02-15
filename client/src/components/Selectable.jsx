import { Check } from 'lucide-react'
import { useMemo, useRef } from 'react'
import { useInteraction } from '../contexts/InteractionContext'

function Selectable({ id, descendantIds = [], children }) {
  const { isSelected } = useInteraction()
  const isParent = descendantIds.length > 0
  const selected = useMemo(() => {
    return !isParent && isSelected(id)
  }, [isParent, isSelected, id])
  const wrapperRef = useRef(null)

  return (
    <div
      ref={wrapperRef}
      data-selectable
      className="relative"
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
