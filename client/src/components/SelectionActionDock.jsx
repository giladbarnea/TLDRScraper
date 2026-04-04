import { BookOpen, Check, ExternalLink, GitMerge, Sparkles, Trash2, X } from 'lucide-react'

function DockButton({ label, icon, onClick, disabled = false, danger = false, accent = false, style }) {
  const buttonBaseClassName = 'group flex min-w-16 flex-col items-center gap-1 rounded-xl px-2 py-1 text-slate-100 transition-all duration-200 ease-[var(--ease-springy)] hover:-translate-y-0.5 hover:text-white active:translate-y-0 active:scale-[0.96] disabled:opacity-35 disabled:hover:translate-y-0 disabled:hover:text-slate-100 disabled:active:scale-100 motion-safe:animate-dock-action-enter'
  const iconClassName = [
    'flex h-11 w-11 items-center justify-center rounded-full transition-transform duration-200 ease-[var(--ease-springy)] group-hover:scale-105 group-active:scale-95',
    accent ? 'bg-brand-500/85 text-white' : '',
    danger ? 'bg-red-500/75 text-white' : '',
    !accent && !danger ? 'bg-white/10 text-white' : '',
  ].join(' ')

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={buttonBaseClassName}
      style={style}
      aria-label={label}
    >
      <span className={iconClassName}>{icon}</span>
      <span className="text-xs font-medium tracking-wide text-center leading-none">{label}</span>
    </button>
  )
}

function SelectionActionDock({
  isSelectMode,
  selectedCount,
  isDigestLoading,
  canOpenSingleSummary,
  isSingleSummaryLoading,
  isSummarizeEachDisabled,
  onClearSelection,
  onMarkRead,
  onMarkRemoved,
  onTriggerDigest,
  onSummarizeSingle,
  onBrowseSingle,
  onSummarizeEach,
}) {
  const actions = [
    {
      key: 'deselect',
      label: 'Deselect',
      icon: <X size={21} />,
      onClick: onClearSelection,
    },
    {
      key: 'read',
      label: 'Read',
      icon: <Check size={21} />,
      onClick: onMarkRead,
    },
    {
      key: 'remove',
      label: 'Remove',
      icon: <Trash2 size={21} />,
      onClick: onMarkRemoved,
      danger: true,
    },
  ]

  if (selectedCount === 1) {
    actions.push({
      key: 'summarize-single',
      label: canOpenSingleSummary ? 'Open' : (isSingleSummaryLoading ? 'Loading...' : 'Summarize'),
      icon: canOpenSingleSummary ? <BookOpen size={21} /> : <Sparkles size={21} />,
      onClick: onSummarizeSingle,
      disabled: isSingleSummaryLoading,
      accent: true,
    })
    actions.push({
      key: 'browse',
      label: 'Browse',
      icon: <ExternalLink size={21} />,
      onClick: onBrowseSingle,
    })
  }

  if (selectedCount > 1) {
    actions.push({
      key: 'digest',
      label: isDigestLoading ? 'Loading...' : 'Digest',
      icon: <GitMerge size={21} />,
      onClick: onTriggerDigest,
      disabled: isDigestLoading,
      accent: true,
    })
    actions.push({
      key: 'summarize-each',
      label: 'Summarize Each',
      icon: <Sparkles size={21} />,
      onClick: onSummarizeEach,
      disabled: isSummarizeEachDisabled,
    })
  }

  return (
    <div
      className={[
        'fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-[calc(env(safe-area-inset-bottom)+0.9rem)] pt-3 transition-all duration-300',
        isSelectMode ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0 pointer-events-none'
      ].join(' ')}
    >
      <div className="w-full max-w-md rounded-[1.7rem] border border-slate-900/10 bg-slate-950/95 text-white shadow-2xl backdrop-blur-xl">
        <div className="flex items-start justify-between gap-1 px-2 py-3">
          {actions.map((action, index) => (
            <DockButton
              key={action.key}
              label={action.label}
              icon={action.icon}
              onClick={action.onClick}
              disabled={action.disabled}
              danger={action.danger}
              accent={action.accent}
              style={{ animationDelay: `${index * 30}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export default SelectionActionDock
