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
          <div className={`
            text-slate-400 transition-all duration-200 ease-out
            ${isFolded ? 'opacity-100 rotate-0' : 'opacity-0 rotate-90 pointer-events-none'}
          `}>
            <ChevronRight size={18} strokeWidth={2.5} />
          </div>
        </div>
      </div>

      <div 
        className="grid transition-[grid-template-rows,opacity] duration-300 ease-out"
        style={{ gridTemplateRows: isFolded ? '0fr' : '1fr' }}
      >
        <div className="overflow-hidden">
          <div className={`
            transition-opacity duration-200
            ${isFolded ? 'opacity-0' : 'opacity-100 delay-75'}
          `}>
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

export default FoldableContainer
