import { MoreHorizontal } from 'lucide-react'
import { useState } from 'react'

function ActionMenu({ title }) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const handleOpen = event => {
    event.stopPropagation()
    setIsMenuOpen(true)
  }

  const handleClose = event => {
    event.stopPropagation()
    setIsMenuOpen(false)
  }

  const handleSelect = event => {
    event.stopPropagation()
  }

  return (
    <>
      <button
        type="button"
        aria-label="Open menu"
        aria-expanded={isMenuOpen}
        aria-haspopup="dialog"
        onClick={handleOpen}
        className="inline-flex items-center justify-center rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
      >
        <MoreHorizontal size={18} />
      </button>

      {isMenuOpen && (
        <div className="fixed inset-0 z-[200]" onClick={handleClose}>
          <div className="absolute inset-0 bg-slate-950/40" />
          <div
            className="absolute bottom-0 left-0 right-0 h-[66vh] rounded-t-3xl bg-slate-900 text-slate-100 shadow-2xl"
            onClick={event => event.stopPropagation()}
          >
            <div className="flex h-full flex-col px-6 pb-10 pt-8">
              <div className="text-center text-lg font-semibold text-slate-100">
                {title}
              </div>
              <button
                type="button"
                onClick={handleSelect}
                className="mt-8 w-full rounded-full bg-slate-800 px-6 py-3 text-left text-base font-medium text-slate-100 shadow-inner transition hover:bg-slate-700"
              >
                Select
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default ActionMenu
