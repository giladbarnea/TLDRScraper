import { BookOpen, Check, ExternalLink, FileText, GitMerge, Podcast, Sparkles, Trash2, X } from 'lucide-react'
import LiquidGlassSurface from './visual-effects/LiquidGlassSurface'

// Flat iOS-menu treatment: a thin-stroke outline glyph above an SF Pro-regular
// label, near-black by default, with color used only as a tint on icon+label
// (never a filled chip). The glyph inherits the tint via currentColor.
function DockButton({ label, icon, onClick, disabled = false, danger = false, accent = false, style }) {
  const tintClassName = accent ? 'text-brand-500' : danger ? 'text-red-500' : 'text-[#1d1d1f]'
  const buttonClassName = `group flex min-w-16 flex-col items-center gap-1.5 rounded-xl px-2 py-1 transition-all duration-200 ease-[var(--ease-springy)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.96] disabled:opacity-35 disabled:hover:translate-y-0 disabled:active:scale-100 motion-safe:animate-dock-action-enter ${tintClassName}`

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={buttonClassName}
      style={style}
      aria-label={label}
    >
      <span className="transition-transform duration-200 ease-[var(--ease-springy)] group-hover:scale-105 group-active:scale-95">{icon}</span>
      <span className="text-[0.8rem] font-normal tracking-[-0.01em] text-center leading-none">{label}</span>
    </button>
  )
}

function SelectionActionDock({
  isSelectMode,
  selectedCount,
  isDigestLoading,
  isPodcastLoading,
  canOpenSingleSummary,
  isSingleSummaryLoading,
  isSummarizeEachDisabled,
  onClearSelection,
  onMarkRead,
  onMarkRemoved,
  onTriggerDigest,
  onTriggerPodcast,
  onSummarizeSingle,
  onBrowseSingle,
  onSummarizeEach,
}) {
  const actions = [
    {
      key: 'deselect',
      label: 'Deselect',
      icon: <X size={24} />,
      onClick: onClearSelection,
    },
    {
      key: 'read',
      label: 'Read',
      icon: <Check size={24} />,
      onClick: onMarkRead,
    },
    {
      key: 'remove',
      label: 'Remove',
      icon: <Trash2 size={24} />,
      onClick: onMarkRemoved,
      danger: true,
    },
    {
      key: 'podcast',
      label: isPodcastLoading ? 'Loading...' : 'Podcast',
      icon: <Podcast size={24} />,
      onClick: onTriggerPodcast,
      disabled: isPodcastLoading,
      accent: true,
    }
  ]

  if (selectedCount === 1) {
    actions.push({
      key: 'summarize-single',
      label: canOpenSingleSummary ? 'Open' : (isSingleSummaryLoading ? 'Loading...' : 'Summarize'),
      icon: canOpenSingleSummary ? <BookOpen size={24} /> : <Sparkles size={24} />,
      onClick: onSummarizeSingle,
      disabled: isSingleSummaryLoading,
      accent: true,
    })
    actions.push({
      key: 'browse',
      label: 'Browse',
      icon: <ExternalLink size={24} />,
      onClick: onBrowseSingle,
    })
  }

  if (selectedCount > 1) {
    actions.push({
      key: 'digest',
      label: isDigestLoading ? 'Loading...' : 'Digest',
      icon: <GitMerge size={24} />,
      onClick: onTriggerDigest,
      disabled: isDigestLoading,
      accent: true,
    })
    actions.push({
      key: 'summarize-each',
      label: 'Summarize Each',
      icon: <FileText size={24} />,
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
      <LiquidGlassSurface
        variant="plate"
        className="w-full max-w-md rounded-[1.7rem] overflow-hidden"
      >
        <div className="flex items-center justify-between gap-1 px-2 py-3">
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
      </LiquidGlassSurface>
    </div>
  )
}

export default SelectionActionDock
