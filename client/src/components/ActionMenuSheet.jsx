import { MoreHorizontal } from 'lucide-react'
import { useState } from 'react'

function ActionMenuSheet({ title, onSelect = () => {} }) {
  const [isOpen, setIsOpen] = useState(false)

  const handleToggle = event => {
    event.stopPropagation()
    setIsOpen(previousState => !previousState)
  }

  const handleClose = () => {
    setIsOpen(false)
  }

  const handleSelect = event => {
    event.stopPropagation()
    onSelect()
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleToggle}
        aria-label="Open menu"
        className="flex items-center justify-center rounded-full p-2 text-slate-400 transition hover:bg-slate-200/70 hover:text-slate-600"
      >
        <MoreHorizontal size={20} />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50" onClick={handleClose}>
          <div className="absolute inset-0 bg-slate-950/60" />
          <div
            className="absolute bottom-0 left-0 right-0 h-[66vh] rounded-t-3xl bg-slate-900 text-slate-100 shadow-2xl"
            onClick={event => event.stopPropagation()}
          >
            <div className="flex justify-center pt-8">
              <span className="text-lg font-semibold">{title}</span>
            </div>
            <div className="mt-6 px-6">
              <button
                type="button"
                onClick={handleSelect}
                className="w-full rounded-full bg-slate-800/80 py-3 text-base font-medium text-slate-100 transition hover:bg-slate-700"
              >
                Select
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ActionMenuSheet
