import { useCallback, useEffect, useRef, useState } from 'react'

const CLOSED_MENU_STATE = Object.freeze({
  isOpen: false,
  anchorX: 0,
  anchorY: 0,
})

/**
 * Custom context menu for overlays.
 * Desktop: right-click opens menu at cursor via onContextMenu.
 * Mobile: text selection opens menu below the selection rect via selectionchange,
 * gated on touch state so the menu appears on finger lift, not mid-gesture.
 */
export function useOverlayContextMenu(enabled = true) {
  const [menuState, setMenuState] = useState(CLOSED_MENU_STATE)
  const menuRef = useRef(null)
  const openedBySelectionRef = useRef(false)

  console.log('[ctxmenu] render — enabled:', enabled, '| isOpen:', menuState.isOpen)

  const closeMenu = useCallback(() => {
    console.log('[ctxmenu] closeMenu — openedBySelection:', openedBySelectionRef.current)
    openedBySelectionRef.current = false
    setMenuState(CLOSED_MENU_STATE)
  }, [])

  const handleContextMenu = useCallback((event) => {
    console.log('[ctxmenu] handleContextMenu — enabled:', enabled, '| target:', event.target.tagName)
    if (!enabled) return
    event.preventDefault()
    openedBySelectionRef.current = false
    setMenuState({
      isOpen: true,
      anchorX: event.clientX,
      anchorY: event.clientY,
    })
    console.log('[ctxmenu] opened via right-click at', event.clientX, event.clientY)
  }, [enabled])

  // Mobile: open menu below text selection on finger lift
  useEffect(() => {
    if (!enabled) return
    const isTouch = matchMedia('(pointer: coarse)').matches
    console.log('[ctxmenu] mobile effect — isTouch:', isTouch)
    if (!isTouch) return

    let touchActive = false

    function openMenuFromSelection() {
      const sel = window.getSelection()
      const text = sel?.toString().trim() ?? ''
      console.log('[ctxmenu] openMenuFromSelection — collapsed:', sel?.isCollapsed, '| text:', text.slice(0, 40))
      if (!sel || sel.isCollapsed || !text) return

      const rect = sel.getRangeAt(0).getBoundingClientRect()
      openedBySelectionRef.current = true
      setMenuState({
        isOpen: true,
        anchorX: rect.left + rect.width / 2,
        anchorY: rect.bottom + 12,
      })
      console.log('[ctxmenu] opened via selection at', rect.left + rect.width / 2, rect.bottom + 12)
    }

    function handleSelectionChange() {
      const selection = window.getSelection()
      const text = selection?.toString().trim() ?? ''
      if (!selection || selection.isCollapsed || !text) {
        if (openedBySelectionRef.current) {
          console.log('[ctxmenu] selectionchange — cleared, closing menu')
          closeMenu()
        }
        return
      }
      console.log('[ctxmenu] selectionchange — touchActive:', touchActive, '| text:', text.slice(0, 40))
      if (!touchActive) openMenuFromSelection()
    }

    function handleTouchStart() {
      touchActive = true
      console.log('[ctxmenu] touchstart')
    }
    function handleTouchEnd() {
      touchActive = false
      console.log('[ctxmenu] touchend — will attempt openMenuFromSelection')
      openMenuFromSelection()
    }

    document.addEventListener('selectionchange', handleSelectionChange)
    document.addEventListener('touchstart', handleTouchStart, true)
    document.addEventListener('touchend', handleTouchEnd, true)
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange)
      document.removeEventListener('touchstart', handleTouchStart, true)
      document.removeEventListener('touchend', handleTouchEnd, true)
    }
  }, [enabled, closeMenu])

  // Close on outside pointer or Escape
  useEffect(() => {
    if (!menuState.isOpen) return
    console.log('[ctxmenu] attaching close listeners (menu open)')

    function handlePointerDown(event) {
      const isInsideMenu = menuRef.current?.contains(event.target)
      console.log('[ctxmenu] pointerdown — insideMenu:', isInsideMenu)
      if (isInsideMenu) return
      if (openedBySelectionRef.current) window.getSelection()?.removeAllRanges()
      closeMenu()
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        console.log('[ctxmenu] Escape key — closing')
        closeMenu()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown, true)
    document.addEventListener('keydown', handleKeyDown, true)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown, true)
      document.removeEventListener('keydown', handleKeyDown, true)
    }
  }, [closeMenu, menuState.isOpen])

  return {
    ...menuState,
    menuRef,
    handleContextMenu,
    closeMenu,
  }
}
