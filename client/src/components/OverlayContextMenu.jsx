import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

const MENU_WIDTH_PX = 184
const MENU_EDGE_GAP_PX = 8
const MENU_VERTICAL_PADDING_PX = 12
const MENU_ITEM_HEIGHT_PX = 44

function clampMenuPosition(anchorX, anchorY, actionCount) {
  const menuHeight = actionCount * MENU_ITEM_HEIGHT_PX + MENU_VERTICAL_PADDING_PX
  const maxLeft = window.innerWidth - MENU_WIDTH_PX - MENU_EDGE_GAP_PX
  const maxTop = window.innerHeight - menuHeight - MENU_EDGE_GAP_PX

  return {
    left: Math.max(MENU_EDGE_GAP_PX, Math.min(anchorX, maxLeft)),
    top: Math.max(MENU_EDGE_GAP_PX, Math.min(anchorY, maxTop)),
  }
}

function OverlayContextMenu({ isOpen, anchorX, anchorY, actions, onClose, menuRef }) {
  const firstActionRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return
    firstActionRef.current?.focus({ preventScroll: true })
  }, [isOpen])

  if (!isOpen) return null

  const position = clampMenuPosition(anchorX, anchorY, actions.length)

  function handleActionClick(action) {
    if (action.disabled) return

    window.getSelection()?.removeAllRanges()
    onClose()
    action.onSelect()
  }

  return createPortal(
    <div
      ref={menuRef}
      role="menu"
      aria-label="Reading actions"
      onContextMenu={(event) => event.preventDefault()}
      className="fixed z-[150] w-[184px] overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 p-1.5 text-slate-700 shadow-elevated backdrop-blur-xl motion-safe:animate-overlay-menu-enter"
      style={{ left: position.left, top: position.top }}
    >
      {actions.map((action, index) => (
        <button
          key={action.key}
          ref={index === 0 ? firstActionRef : null}
          type="button"
          role="menuitem"
          disabled={action.disabled}
          onClick={() => handleActionClick(action)}
          className={[
            'flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors',
            'hover:bg-slate-100 focus:bg-slate-100 focus:outline-none disabled:opacity-40',
            action.tone === 'success' ? 'text-green-700 hover:bg-green-50 focus:bg-green-50' : '',
          ].join(' ')}
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-current">
            {action.icon}
          </span>
          <span>{action.label}</span>
        </button>
      ))}
    </div>,
    document.body
  )
}

export default OverlayContextMenu
