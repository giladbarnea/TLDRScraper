import { useCallback, useEffect, useRef, useState } from 'react'

const MenuOpenSource = Object.freeze({
  NONE: 'none',
  DESKTOP: 'desktop',
  MOBILE_SELECTION: 'mobile-selection',
})

const CLOSED_MENU_STATE = Object.freeze({
  isOpen: false,
  anchorX: 0,
  anchorY: 0,
  selectedText: '',
  source: MenuOpenSource.NONE,
})

// CONTRACT — this hook pairs with two things that must cooperate:
//  1. The overlay shell must mark its selectable content surface with
//     `data-overlay-content` (see `BaseOverlay.jsx`). The mobile
//     selection→menu path bails out if the selection's anchor is not inside
//     a `[data-overlay-content]` subtree.
//  2. The overlay's own Escape handler (see `BaseOverlay.jsx`) must guard
//     with `if (event.defaultPrevented) return`. When the menu is open, this
//     hook's Escape listener calls `preventDefault() + stopImmediatePropagation()`
//     in the capture phase so the overlay-close handler is suppressed for that
//     single keypress. Remove that guard and Escape will close menu AND overlay.
export function useOverlayContextMenu(enabled = true) {
  const [menuState, setMenuState] = useState(CLOSED_MENU_STATE)
  const menuRef = useRef(null)
  const menuStateRef = useRef(menuState)

  useEffect(() => {
    menuStateRef.current = menuState
  }, [menuState])

  console.log('[ctxmenu] render — enabled:', enabled, '| isOpen:', menuState.isOpen)

  const openMenu = useCallback(({ source, anchorX, anchorY, selectedText = '' }) => {
    const nextState = {
      isOpen: true,
      anchorX,
      anchorY,
      selectedText,
      source,
    }
    // Mutate the ref synchronously so document listeners that fire between
    // setState and React's commit still see the authoritative `source`.
    // The useEffect mirror above is a backstop for any non-command path.
    menuStateRef.current = nextState
    setMenuState(nextState)
  }, [])

  const closeMenu = useCallback(({ clearSelection = false } = {}) => {
    console.log('[ctxmenu] closeMenu — clearSelection:', clearSelection, '| source:', menuStateRef.current.source)
    if (clearSelection) window.getSelection()?.removeAllRanges()
    menuStateRef.current = CLOSED_MENU_STATE
    setMenuState(CLOSED_MENU_STATE)
  }, [])

  const handleContextMenu = useDesktopContextMenu({ enabled, openMenu })
  useMobileSelectionMenu({ enabled, openMenu, closeMenu, menuStateRef })
  useOverlayMenuDismissal({
    isOpen: menuState.isOpen,
    menuRef,
    closeMenu,
    menuStateRef,
  })

  useEffect(() => {
    if (enabled) return
    closeMenu()
  }, [closeMenu, enabled])

  return {
    isOpen: menuState.isOpen,
    anchorX: menuState.anchorX,
    anchorY: menuState.anchorY,
    selectedText: menuState.selectedText,
    menuRef,
    handleContextMenu,
    closeMenu,
  }
}

function useDesktopContextMenu({ enabled, openMenu }) {
  return useCallback((event) => {
    console.log('[ctxmenu] handleContextMenu — enabled:', enabled, '| target:', event.target.tagName)
    if (!enabled) return

    event.preventDefault()
    openMenu({
      source: MenuOpenSource.DESKTOP,
      anchorX: event.clientX,
      anchorY: event.clientY,
      selectedText: '',
    })
    console.log('[ctxmenu] opened via right-click at', event.clientX, event.clientY)
  }, [enabled, openMenu])
}

function useMobileSelectionMenu({ enabled, openMenu, closeMenu, menuStateRef }) {
  useEffect(() => {
    if (!enabled) return
    const isTouch = matchMedia('(pointer: coarse)').matches
    console.log('[ctxmenu] mobile effect — isTouch:', isTouch)
    if (!isTouch) return

    let touchActive = false

    function readOverlaySelection() {
      const selection = window.getSelection()
      const selectedText = selection?.toString().trim() ?? ''
      if (!selection || selection.isCollapsed || !selectedText) return null
      if (!selection.anchorNode?.parentElement?.closest('[data-overlay-content]')) {
        console.log('[ctxmenu] readOverlaySelection — selection not inside [data-overlay-content], skipping')
        return null
      }

      const rect = selection.getRangeAt(0).getBoundingClientRect()
      return {
        anchorX: rect.left + rect.width / 2,
        anchorY: rect.bottom + 12,
        selectedText,
      }
    }

    function openFromSelection() {
      const selectionMenu = readOverlaySelection()
      if (!selectionMenu) return
      openMenu({
        source: MenuOpenSource.MOBILE_SELECTION,
        ...selectionMenu,
      })
      console.log('[ctxmenu] opened via selection at', selectionMenu.anchorX, selectionMenu.anchorY, '| text:', selectionMenu.selectedText.slice(0, 40))
    }

    function handleSelectionChange() {
      const selectionMenu = readOverlaySelection()
      const openedFromMobileSelection =
        menuStateRef.current.source === MenuOpenSource.MOBILE_SELECTION

      if (!selectionMenu) {
        // Guard: don't close the menu mid-touch. On mobile a tap on the menu
        // button collapses the selection (touchstart) before click fires —
        // closing here would ghost-click whatever is underneath the menu.
        if (openedFromMobileSelection && !touchActive) {
          console.log('[ctxmenu] selectionchange — cleared (not touching), closing menu')
          closeMenu()
        } else if (openedFromMobileSelection) {
          console.log('[ctxmenu] selectionchange — cleared but touchActive, keeping menu open to avoid ghost click')
        }
        return
      }

      console.log('[ctxmenu] selectionchange — touchActive:', touchActive, '| text:', selectionMenu.selectedText.slice(0, 40))
      if (!touchActive) openFromSelection()
    }

    function handleTouchStart() {
      touchActive = true
      console.log('[ctxmenu] touchstart')
    }

    function handleTouchEnd() {
      touchActive = false
      console.log('[ctxmenu] touchend — will attempt openFromSelection')
      openFromSelection()
    }

    document.addEventListener('selectionchange', handleSelectionChange)
    document.addEventListener('touchstart', handleTouchStart, true)
    document.addEventListener('touchend', handleTouchEnd, true)

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange)
      document.removeEventListener('touchstart', handleTouchStart, true)
      document.removeEventListener('touchend', handleTouchEnd, true)
    }
  }, [enabled, openMenu, closeMenu, menuStateRef])
}

function useOverlayMenuDismissal({ isOpen, menuRef, closeMenu, menuStateRef }) {
  useEffect(() => {
    if (!isOpen) return
    console.log('[ctxmenu] attaching close listeners (menu open)')

    function handlePointerDown(event) {
      const isInsideMenu = menuRef.current?.contains(event.target)
      console.log('[ctxmenu] pointerdown — insideMenu:', isInsideMenu)
      if (isInsideMenu) return

      closeMenu({
        clearSelection:
          menuStateRef.current.source === MenuOpenSource.MOBILE_SELECTION,
      })
    }

    function handleKeyDown(event) {
      if (event.key !== 'Escape') return

      console.log('[ctxmenu] Escape — closing menu (arbitrating over BaseOverlay)')
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
  }, [closeMenu, isOpen, menuRef, menuStateRef])
}
