import { MoreVertical } from 'lucide-react'

function ThreeDotMenuButton({ onClick }) {
  const handleClick = (e) => {
    e.stopPropagation()
    onClick()
  }

  return (
    <button
      onClick={handleClick}
      className="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
      aria-label="Open menu"
    >
      <MoreVertical size={20} />
    </button>
  )
}

export default ThreeDotMenuButton
