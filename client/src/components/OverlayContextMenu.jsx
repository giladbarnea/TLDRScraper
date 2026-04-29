import {
  autoUpdate,
  FloatingFocusManager,
  FloatingNode,
  FloatingPortal,
  flip,
  inline,
  offset,
  shift,
  useDismiss,
  useFloating,
  useFloatingNodeId,
  useInteractions,
} from '@floating-ui/react'
import { useCallback, useEffect, useMemo } from 'react'

const MENU_EDGE_GAP_PX = 8

function createVirtualReference(positionReference) {
  return {
    getBoundingClientRect: () => positionReference.boundingRect,
    getClientRects: () => positionReference.clientRects,
  }
}

function OverlayContextMenu({ isOpen, positionReference, actions, onOpenChange, selectedText }) {
  const nodeId = useFloatingNodeId()
  const isCoarsePointer = matchMedia('(pointer: coarse)').matches

  const middleware = useMemo(() => {
    const list = []
    if (positionReference?.kind === 'range') list.push(inline())
    list.push(offset(positionReference?.offsetPx ?? 0))
    list.push(flip())
    list.push(shift({ padding: MENU_EDGE_GAP_PX }))
    return list
  }, [positionReference?.kind, positionReference?.offsetPx])

  const { refs, floatingStyles, context } = useFloating({
    nodeId,
    open: isOpen,
    onOpenChange,
    placement: positionReference?.placement ?? 'bottom-start',
    strategy: 'fixed',
    transform: false,
    whileElementsMounted: autoUpdate,
    middleware,
  })
  const dismiss = useDismiss(context, {
    escapeKey: true,
    outsidePress: true,
    outsidePressEvent: isCoarsePointer ? 'click' : 'pointerdown',
  })
  const { getFloatingProps } = useInteractions([dismiss])

  const virtualReference = useMemo(
    () => positionReference ? createVirtualReference(positionReference) : null,
    [positionReference]
  )

  useEffect(() => {
    refs.setPositionReference(virtualReference)
  }, [refs, virtualReference])

  const setMenuNode = useCallback((node) => {
    refs.setFloating(node)
  }, [refs])

  if (!isOpen) return null

  function handleActionClick(action) {
    if (action.disabled) return

    const text = selectedText || window.getSelection()?.toString() || ''
    console.log('[ctxmenu] action click — key:', action.key, '| text:', text.slice(0, 40), '| live:', window.getSelection()?.toString()?.slice(0, 40))
    window.getSelection()?.removeAllRanges()
    onOpenChange(false)
    action.onSelect(text)
  }

  return (
    <FloatingNode id={nodeId}>
      <FloatingPortal>
        <FloatingFocusManager
          context={context}
          modal={false}
          initialFocus={isCoarsePointer ? -1 : 0}
          returnFocus={!isCoarsePointer}
        >
          <div
            {...getFloatingProps({
              ref: setMenuNode,
              role: 'menu',
              'aria-label': 'Reading actions',
              onClick: (event) => event.stopPropagation(),
              onContextMenu: (event) => event.preventDefault(),
              className: 'fixed z-[150] w-[184px] overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 p-1.5 text-slate-700 shadow-elevated backdrop-blur-xl motion-safe:animate-overlay-menu-enter',
              style: floatingStyles,
            })}
          >
            {actions.map((action) => (
              <button
                key={action.key}
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
          </div>
        </FloatingFocusManager>
      </FloatingPortal>
    </FloatingNode>
  )
}

export default OverlayContextMenu
