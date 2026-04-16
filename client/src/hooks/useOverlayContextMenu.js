import { useCallback, useEffect, useRef, useState } from 'react'

const CLOSED_MENU_STATE = Object.freeze({
  isOpen: false,
  anchorX: 0,
  anchorY: 0,
})

export function useOverlayContextMenu(enabled = true) {
  const [menuState, setMenuState] = useState(CLOSED_MENU_STATE)
  const menuRef = useRef(null)
  const openedBySelectionRef = useRef(false)

  const closeMenu = useCallback(() => {
    openedBySelectionRef.current = false
    setMenuState(CLOSED_MENU_STATE)
  }, [])

  const handleContextMenu = useCallback((event) => {
    if (!enabled) return

    event.preventDefault()
    setMenuState({
      isOpen: true,
      anchorX: event.clientX,
      anchorY: event.clientY,
    })
  }, [enabled])

  useEffect(() => {
    if (!enabled) return
    if (!matchMedia('(pointer: coarse)').matches) return

    let touchActive = false

    function openMenuFromSelection() {
      const sel = window.getSelection()
      if (!sel || sel.isCollapsed || !sel.toString().trim()) return

      if (!sel.anchorNode?.parentElement?.closest('[data-overlay-content]')) return

      const range = sel.getRangeAt(0)
      const rect = range.getBoundingClientRect()

      openedBySelectionRef.current = true
      setMenuState({
        isOpen: true,
        anchorX: rect.left + rect.width / 2,
        anchorY: rect.bottom + 12,
      })
    }

    function handleSelectionChange() {
      const selection = window.getSelection()
      if (!selection || selection.isCollapsed || !selection.toString().trim()) {
        if (openedBySelectionRef.current) closeMenu()
        return
      }
      if (!touchActive) openMenuFromSelection()
    }

    function handleTouchStart() { touchActive = true }
    function handleTouchEnd() {
      touchActive = false
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

  useEffect(() => {
    if (enabled) return
    closeMenu()
  }, [closeMenu, enabled])

  useEffect(() => {
    if (!menuState.isOpen) return

    function handlePointerDown(event) {
      if (menuRef.current?.contains(event.target)) return
      if (openedBySelectionRef.current) window.getSelection()?.removeAllRanges()
      closeMenu()
    }

    function handleKeyDown(event) {
      if (event.key !== 'Escape') return

      event.preventDefault()
      event.stopPropagation()
      event.stopImmediatePropagation()
      closeMenu()
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
