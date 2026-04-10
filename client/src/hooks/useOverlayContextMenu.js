import { useCallback, useEffect, useRef, useState } from 'react'

const CLOSED_MENU_STATE = Object.freeze({
  isOpen: false,
  anchorX: 0,
  anchorY: 0,
})

export function useOverlayContextMenu(enabled = true) {
  const [menuState, setMenuState] = useState(CLOSED_MENU_STATE)
  const menuRef = useRef(null)

  const closeMenu = useCallback(() => {
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
    if (enabled) return
    closeMenu()
  }, [closeMenu, enabled])

  useEffect(() => {
    if (!menuState.isOpen) return

    function handlePointerDown(event) {
      if (menuRef.current?.contains(event.target)) return
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
