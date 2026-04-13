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

    let debounceTimer = null

    function handleSelectionChange() {
      const selection = window.getSelection()
      if (!selection || selection.isCollapsed || !selection.toString().trim()) {
        clearTimeout(debounceTimer)
        if (openedBySelectionRef.current) closeMenu()
        return
      }

      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        const sel = window.getSelection()
        if (!sel || sel.isCollapsed || !sel.toString().trim()) return

        const range = sel.getRangeAt(0)
        const rect = range.getBoundingClientRect()
        console.log('[ctx:selection] opening menu below rect bottom:', rect.bottom.toFixed(0))

        openedBySelectionRef.current = true
        setMenuState({
          isOpen: true,
          anchorX: rect.left + rect.width / 2,
          anchorY: rect.bottom + 12,
        })
      }, 200)
    }

    document.addEventListener('selectionchange', handleSelectionChange)
    return () => {
      clearTimeout(debounceTimer)
      document.removeEventListener('selectionchange', handleSelectionChange)
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
