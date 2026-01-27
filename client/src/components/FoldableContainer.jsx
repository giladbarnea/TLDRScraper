import { ChevronRight } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage'

function FoldableContainer({ id, title, children, defaultFolded = false, className = '', headerClassName = '', contentClassName = '', dataAttributes = {} }) {
  const [isFolded, setIsFolded] = useLocalStorage(id, defaultFolded)
  const prevDefaultFolded = useRef(defaultFolded)

  useEffect(() => {
    if (defaultFolded && !prevDefaultFolded.current) {
      setIsFolded(true)
    }
    prevDefaultFolded.current = defaultFolded
  }, [defaultFolded, setIsFolded])

  return (
    <div
      data-is-folded={isFolded}
      {...dataAttributes}
      className={`transition-all duration-300 ${className}`}
    >
      <div 
        onClick={() => setIsFolded(!isFolded)}
        className={`cursor-pointer group select-none flex items-center ${headerClassName}`}
      >
        <div className="flex-grow min-w-0">
          {title}
        </div>
        
        <div className={`
          text-slate-400 transition-all duration-300 transform ml-4
          ${isFolded ? '' : 'rotate-90'}
        `}>
          <ChevronRight size={20} />
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
