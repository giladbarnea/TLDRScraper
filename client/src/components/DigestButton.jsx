import { Sparkles } from 'lucide-react'
import { useInteraction } from '../contexts/InteractionContext'

function DigestButton({ onClick, loading }) {
  const { isSelectMode, selectedIds } = useInteraction()

  if (!isSelectMode) return null

  return (
    <button
      onClick={onClick}
      disabled={loading || selectedIds.size === 0}
      className="flex items-center gap-1.5 bg-brand-500 text-white px-3 py-1.5 rounded-full text-sm font-medium hover:bg-brand-600 disabled:opacity-60 disabled:cursor-not-allowed"
    >
      <Sparkles size={14} />
      {loading ? 'Digesting...' : 'Digest'}
    </button>
  )
}

export default DigestButton
