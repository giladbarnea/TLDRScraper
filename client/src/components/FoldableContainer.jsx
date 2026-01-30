import { ChevronRight } from 'lucide-react'
import { useEffect } from 'react'
import { useInteraction } from '../contexts/InteractionContext'

function FoldableContainer({ id, title, children, defaultFolded = false, className = '', headerClassName = '', contentClassName = '', dataAttributes = {} }) {
  const { isExpanded, containerShortPress, setExpanded } = useInteraction()
  const expanded = isExpanded(id)
  const isFolded = !expanded

  useEffect(() => {
    if (defaultFolded) {
      setExpanded(id, false)
    }
  }, [defaultFolded, id, setExpanded])

  return (
    <div
      data-is-folded={isFolded}
      {...dataAttributes}
      className={`transition-all duration-300 ${className}`}
    >
      <div className={`flex items-center ${headerClassName}`}>
        <div
          onClick={() => containerShortPress(id)}
          data-fold-toggle
          className="cursor-pointer group select-none flex items-center flex-1"
        >
          <div className="flex-grow-0">
            {title}
          </div>

          <div className={`
            text-slate-400 transition-all duration-300 transform ml-4
            ${isFolded ? '' : 'rotate-90'}
          `}>
            <ChevronRight size={20} />
          </div>
        </div>
      </div>

      <div className={`
        grid transition-all duration-500 ease-in-out
        ${isFolded ? 'grid-rows-[0fr] opacity-0' : 'grid-rows-[1fr] opacity-100'}
      `}>
        <div className={`overflow-hidden ${contentClassName}`}>
           {children}
        </div>
      </div>
    </div>
  )
}

export default FoldableContainer
