import { ContextMenu } from '@base-ui-components/react/context-menu'
import { autoUpdate, flip, inline, offset, shift, useFloating } from '@floating-ui/react'
import { useCallback, useEffect, useMemo } from 'react'

const MENU_EDGE_GAP_PX = 8

function createVirtualReference(positionReference) {
  return {
    getBoundingClientRect: () => positionReference.boundingRect,
    getClientRects: () => positionReference.clientRects,
  }
}

function OverlayContextMenu({ isOpen, positionReference, actions, onOpenChange, selectedText }) {
  const isCoarsePointer = matchMedia('(pointer: coarse)').matches

  const middleware = useMemo(() => {
    const list = []
    if (positionReference?.kind === 'range') list.push(inline())
    list.push(offset(positionReference?.offsetPx ?? 0))
    list.push(flip())
    list.push(shift({ padding: MENU_EDGE_GAP_PX }))
    return list
  }, [positionReference?.kind, positionReference?.offsetPx])

  const { refs, floatingStyles } = useFloating({
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
    refs.setPositionReference(virtualReference)
  }, [refs, virtualReference])

  const handleMenuOpenChange = useCallback((open, eventDetails) => {
    const reason = eventDetails?.reason === 'outside-press' ? 'outside-press' : undefined
    onOpenChange(open, eventDetails?.event, reason)
  }, [onOpenChange])

  if (!isOpen) return null

  function handleActionClick(action) {
    if (action.disabled) return

    const text = selectedText || window.getSelection()?.toString() || ''
    window.getSelection()?.removeAllRanges()
    onOpenChange(false)
    action.onSelect(text)
  }

  return (
    <ContextMenu.Root open={isOpen} onOpenChange={handleMenuOpenChange} modal={false}>
      <ContextMenu.Portal>
        <ContextMenu.Positioner
          sideOffset={0}
          style={floatingStyles}
          className="fixed z-[150]"
          ref={refs.setFloating}
        >
          <ContextMenu.Popup
            role="menu"
            aria-label="Reading actions"
            onClick={(event) => event.stopPropagation()}
            onContextMenu={(event) => event.preventDefault()}
            className="w-[184px] overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 p-1.5 text-slate-700 shadow-elevated backdrop-blur-xl motion-safe:animate-overlay-menu-enter"
          >
            {actions.map((action) => (
              <ContextMenu.Item
                key={action.key}
                disabled={action.disabled}
                closeOnSelect={!isCoarsePointer}
                onSelect={(event) => {
                  event.preventDefault()
                  handleActionClick(action)
                }}
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
              </ContextMenu.Item>
            ))}
          </ContextMenu.Popup>
        </ContextMenu.Positioner>
      </ContextMenu.Portal>
    </ContextMenu.Root>
  )
}

export default OverlayContextMenu
