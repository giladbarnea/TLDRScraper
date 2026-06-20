import { ChevronRight } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { interactionActions, useIsExpanded } from '../store/articleStore'

function FoldableContainer({ id, title, children, defaultFolded = false, className = '', headerClassName = '', contentClassName = '', dataAttributes = {} }) {
  const expanded = useIsExpanded(id)
  const isFolded = !expanded
  const wasAutoFoldedRef = useRef(defaultFolded)

  useEffect(() => {
    if (defaultFolded) {
      interactionActions.setExpanded(id, false)
      // Only on the live exhaustion edge (not the initial already-removed mount).
      if (!wasAutoFoldedRef.current) interactionActions.expandFirstLeafAfterContainer(id)
    }
    wasAutoFoldedRef.current = defaultFolded
  }, [defaultFolded, id])

  return (
    <div
      data-is-folded={isFolded}
      {...dataAttributes}
      className={`transition-all duration-300 ${className}`}
    >
      <div className={`flex items-center ${headerClassName}`}>
        <div
          onClick={() => interactionActions.containerShortPress(id)}
          data-fold-toggle
          className="cursor-pointer group select-none flex items-center flex-1"
        >
          <div className="flex-grow-0">
            {title}
          </div>

          <div className={`
            text-slate-400 transition-all duration-300 transform ml-2
            ${isFolded ? '' : 'rotate-90'}
          `}>
            <ChevronRight size={18} />
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
