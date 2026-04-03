import { GitMerge, X } from 'lucide-react'

function SelectionActionDock({ isSelectMode, selectedCount, isDigestLoading, onClearSelection, onTriggerDigest }) {
  const isDigestDisabled = selectedCount < 2 || isDigestLoading

  return (
    <div
      className={[
        'fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-[calc(env(safe-area-inset-bottom)+0.9rem)] pt-3 transition-all duration-300',
        isSelectMode ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0 pointer-events-none'
      ].join(' ')}
    >
      <div className="w-full max-w-md rounded-[1.7rem] border border-slate-900/10 bg-slate-950/95 text-white shadow-2xl backdrop-blur-xl">
        <div className="flex items-center justify-around px-4 py-3">
          <button
            type="button"
            onClick={onClearSelection}
            className="flex min-w-20 flex-col items-center gap-1 rounded-xl px-3 py-1 text-slate-100 transition-colors hover:text-white"
            aria-label="Clear selection"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/10">
              <X size={21} />
            </span>
            <span className="text-xs font-medium tracking-wide">Deselect</span>
          </button>

          <button
            type="button"
            onClick={onTriggerDigest}
            disabled={isDigestDisabled}
            className="flex min-w-20 flex-col items-center gap-1 rounded-xl px-3 py-1 text-slate-100 transition-colors hover:text-white disabled:opacity-35 disabled:hover:text-slate-100"
            aria-label="Generate digest"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-brand-500/85 text-white">
              <GitMerge size={21} />
            </span>
            <span className="text-xs font-medium tracking-wide">{isDigestLoading ? 'Loading...' : 'Digest'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default SelectionActionDock
