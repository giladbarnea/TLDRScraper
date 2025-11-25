import { ChevronRight } from 'lucide-react'
import { useFoldState } from '../hooks/useFoldState'

function FoldableContainer({ id, title, children, className = '', headerClassName = '' }) {
  const { isFolded, toggleFold } = useFoldState(id)

  return (
    <div className={className}>
      <div
        onClick={toggleFold}
        className={`cursor-pointer select-none ${headerClassName}`}
      >
        <div className="flex items-center gap-2">
          {title}
          {isFolded && <ChevronRight size={16} className="text-slate-400 shrink-0" />}
        </div>
      </div>
      <div className={isFolded ? 'hidden' : ''}>
        {children}
      </div>
    </div>
  )
}

export default FoldableContainer
