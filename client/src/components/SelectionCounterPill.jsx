import { X } from 'lucide-react'
import { useSelection } from '../contexts/SelectionContext'

function SelectionCounterPill() {
  const { selectedIds, isSelectMode, clear } = useSelection()

  if (!isSelectMode) return null

  return (
    <div className="flex items-center gap-2 bg-slate-900 text-white px-3 py-1.5 rounded-full text-sm font-medium">
      <button
        onClick={clear}
        className="hover:bg-white/20 rounded-full p-0.5 transition-colors"
      >
        <X size={16} />
      </button>
      <span>{selectedIds.size}</span>
    </div>
  )
}

export default SelectionCounterPill
