import { autoUpdate, flip, inline, offset, shift, useFloating } from '@floating-ui/react-dom'
import { useCallback, useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'

const MENU_EDGE_GAP_PX = 8

function createVirtualReference(positionReference) {
  return {
    getBoundingClientRect: () => positionReference.boundingRect,
    getClientRects: () => positionReference.clientRects,
  }
}

function OverlayContextMenu({ isOpen, positionReference, actions, onClose, menuRef, selectedText }) {
  const firstActionRef = useRef(null)

  const middleware = useMemo(() => {
    const list = []
    if (positionReference?.kind === 'range') list.push(inline())
    list.push(offset(positionReference?.offsetPx ?? 0))
    list.push(flip())
    list.push(shift({ padding: MENU_EDGE_GAP_PX }))
    return list
  }, [positionReference?.kind, positionReference?.offsetPx])

  const { refs: floatingRefs, floatingStyles, isPositioned } = useFloating({
    open: isOpen,
    placement: positionReference?.placement ?? 'bottom-start',
    strategy: 'fixed',
    transform: false,
    whileElementsMounted: autoUpdate,
    middleware,
  })

  const virtualReference = useMemo(
    () => positionReference ? createVirtualReference(positionReference) : null,
    [positionReference]
  )

  useEffect(() => {
    floatingRefs.setReference(virtualReference)
  }, [floatingRefs, virtualReference])

  const setMenuNode = useCallback((node) => {
    menuRef.current = node
    floatingRefs.setFloating(node)
  }, [menuRef, floatingRefs])

  useEffect(() => {
    if (!isOpen) return
    if (matchMedia('(pointer: coarse)').matches) return
    firstActionRef.current?.focus({ preventScroll: true })
  }, [isOpen])

  if (!isOpen) return null

  function handleActionClick(action) {
    if (action.disabled) return

    const text = selectedText || window.getSelection()?.toString() || ''
    console.log('[ctxmenu] action click — key:', action.key, '| text:', text.slice(0, 40), '| live:', window.getSelection()?.toString()?.slice(0, 40))
    window.getSelection()?.removeAllRanges()
    onClose()
    action.onSelect(text)
  }

  return createPortal(
    <div
      ref={setMenuNode}
      role="menu"
      aria-label="Reading actions"
      onClick={(e) => e.stopPropagation()}
      onContextMenu={(event) => event.preventDefault()}
      className="fixed z-[150] w-[184px] overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 p-1.5 text-slate-700 shadow-elevated backdrop-blur-xl motion-safe:animate-overlay-menu-enter"
      style={{ ...floatingStyles, visibility: isPositioned ? 'visible' : 'hidden' }}
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
