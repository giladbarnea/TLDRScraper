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
    left: Math.max(MENU_EDGE_GAP_PX, Math.min(anchorX - MENU_WIDTH_PX / 2, maxLeft)),
    top: Math.max(MENU_EDGE_GAP_PX, Math.min(anchorY, maxTop)),
  }
}

function OverlayContextMenu({ isOpen, anchorX, anchorY, actions, onClose, menuRef }) {
  const firstActionRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return
    if (matchMedia('(pointer: coarse)').matches) return
    firstActionRef.current?.focus({ preventScroll: true })
  }, [isOpen])

  if (!isOpen) return null

  const { left, top } = clampMenuPosition(anchorX, anchorY, actions.length)

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
      className="fixed z-[200] min-w-[184px] py-1.5 bg-white rounded-xl shadow-lg border border-slate-200/80 animate-context-menu-in"
      style={{ left, top }}
    >
      {actions.map((action, index) => (
        <button
          key={action.label}
          ref={index === 0 ? firstActionRef : undefined}
          role="menuitem"
          disabled={action.disabled}
          onClick={() => handleActionClick(action)}
          className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-left text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-default transition-colors"
        >
          <span className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 text-current">
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
