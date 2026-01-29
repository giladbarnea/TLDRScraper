import { useState } from 'react'
import BottomSheet from './BottomSheet'
import ThreeDotMenuButton from './ThreeDotMenuButton'

function Selectable({ id, title, children }) {
  const [menuOpen, setMenuOpen] = useState(false)

  const handleSelect = () => {
    const storageKey = 'podcastSources-1'
    const existing = JSON.parse(localStorage.getItem(storageKey) || '[]')
    if (!existing.includes(id)) {
      existing.push(id)
      localStorage.setItem(storageKey, JSON.stringify(existing))
    }
    setMenuOpen(false)
  }

  const openMenu = () => setMenuOpen(true)
  const menuButton = <ThreeDotMenuButton onClick={openMenu} />

  return (
    <>
      {children({ menuButton, openMenu })}

      <BottomSheet
        isOpen={menuOpen}
        onClose={() => setMenuOpen(false)}
        title={title}
      >
        <button
          onClick={handleSelect}
          className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 rounded-xl text-slate-700 font-medium transition-colors"
        >
          Select
        </button>
      </BottomSheet>
    </>
  )
}

export default Selectable
