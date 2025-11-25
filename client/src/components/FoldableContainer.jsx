import { ChevronRight } from 'lucide-react'
import { useState } from 'react'

function FoldableContainer({ title, children, defaultFolded = false, className = '', headerClassName = '', contentClassName = '' }) {
  const [isFolded, setIsFolded] = useState(defaultFolded)

  return (
    <div className={`transition-all duration-300 ${className}`}>
      <div 
        onClick={() => setIsFolded(!isFolded)}
        className={`cursor-pointer group select-none flex items-center justify-between ${headerClassName}`}
      >
        <div className="flex-grow">
          {title}
        </div>
        
        {/* Chevron - only visible when folded */}
        <div className={`
          text-slate-400 transition-all duration-300 transform
          ${isFolded ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-2 pointer-events-none'}
        `}>
          <ChevronRight size={20} />
        </div>
      </div>

      <div className={`
        overflow-hidden transition-all duration-500 ease-in-out
        ${isFolded ? 'max-h-0 opacity-0' : 'max-h-[5000px] opacity-100'}
      `}>
        {/* 
          We use display: none (via hidden class or similar logic if needed for strict unmounting) 
          or just reliance on max-h-0 and overflow-hidden for the "roll" effect.
          However, to ensure "passive" state preservation, we must keep the children mounted.
          The CSS transition above keeps them mounted but hidden.
        */}
        <div className={`${isFolded ? 'invisible' : 'visible'} ${contentClassName}`}>
           {children}
        </div>
      </div>
    </div>
  )
}

export default FoldableContainer
