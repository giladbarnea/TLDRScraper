import { useCallback, useEffect, useRef, useState } from 'react'
import {
  createInitialMobileSelectionMenuState,
  MobileSelectionMenuDecisionType,
  MobileSelectionMenuEventType,
  reduceMobileSelectionMenu,
} from '../reducers/mobileSelectionMenuReducer'

const LONG_PRESS_DELAY_MS = 520

const MenuOpenSource = Object.freeze({
  NONE: 'none',
  DESKTOP: 'desktop',
  MOBILE_SELECTION: 'mobile-selection',
  LINK: 'link',
})

const CLOSED_MENU_STATE = Object.freeze({
  isOpen: false,
  positionReference: null,
  selectedText: '',
  source: MenuOpenSource.NONE,
  actionContext: null,
})

function copyDomRect(rect) {
  return { x: rect.x, y: rect.y, top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height }
}

function createPointPositionReference(x, y) {
  return {
    kind: 'point',
    boundingRect: { x, y, top: y, left: x, right: x, bottom: y, width: 0, height: 0 },
    clientRects: [],
    placement: 'bottom-start',
    offsetPx: 0,
  }
}

function createElementPositionReference(element) {
  const boundingRect = copyDomRect(element.getBoundingClientRect())
  return {
    kind: 'element',
    boundingRect,
    clientRects: [boundingRect],
    placement: 'bottom',
    offsetPx: 10,
  }
}

function readOverlaySelection() {
  const selection = window.getSelection()
  const selectedText = selection?.toString().trim() ?? ''
  if (!selection || selection.isCollapsed || !selectedText) return null

  const anchorElement = selection.anchorNode instanceof Element
    ? selection.anchorNode
    : selection.anchorNode?.parentElement
  if (!anchorElement?.closest('[data-overlay-content]')) {
    console.log('[ctxmenu] readOverlaySelection — selection not inside [data-overlay-content], skipping')
    return null
  }

  const range = selection.getRangeAt(0)
  const boundingRect = copyDomRect(range.getBoundingClientRect())
  const clientRects = Array.from(range.getClientRects()).map(copyDomRect)
  if (clientRects.length === 0) return null

  return {
    selectedText,
    positionReference: {
      kind: 'range',
      boundingRect,
      clientRects,
      placement: 'bottom',
      offsetPx: 12,
    },
  }
}

function readAnchorContext(target) {
  const anchor = target.closest?.('[data-overlay-content] a[href]')
  if (!anchor) return null

  return {
    anchorElement: anchor,
    selectedText: anchor.textContent.trim() || anchor.href,
    positionReference: createElementPositionReference(anchor),
    actionContext: {
      kind: 'link',
      url: anchor.href,
      label: anchor.textContent.trim() || anchor.href,
    },
  }
}

export function useOverlayContextMenu(enabled = true) {
  const [menuState, setMenuState] = useState(CLOSED_MENU_STATE)
  const menuStateRef = useRef(menuState)
  const resetMobileSelectionStateRef = useRef(() => {})

  useEffect(() => {
    menuStateRef.current = menuState
  }, [menuState])

  console.log('[ctxmenu] render — enabled:', enabled, '| isOpen:', menuState.isOpen)

  const openMenu = useCallback(({ source, positionReference, selectedText = '', actionContext = null }) => {
    const nextState = {
      isOpen: true,
      positionReference,
      selectedText,
      source,
      actionContext,
    }
    menuStateRef.current = nextState
    setMenuState(nextState)
  }, [])

  const closeMenu = useCallback(({ clearSelection = false } = {}) => {
    console.log('[ctxmenu] closeMenu — clearSelection:', clearSelection, '| source:', menuStateRef.current.source)
    resetMobileSelectionStateRef.current()
    if (clearSelection) window.getSelection()?.removeAllRanges()
    menuStateRef.current = CLOSED_MENU_STATE
    setMenuState(CLOSED_MENU_STATE)
  }, [])

  const onOpenChange = useCallback((open, _event, reason) => {
    if (open) return

    closeMenu({
      clearSelection:
        reason === 'outside-press'
        && menuStateRef.current.source === MenuOpenSource.MOBILE_SELECTION,
    })
  }, [closeMenu])

  const handleContextMenu = useDesktopContextMenu({ enabled, openMenu })
  useMobileSelectionMenu({ enabled, openMenu, closeMenu, resetMobileSelectionStateRef })
  useLinkLongPressMenu({ enabled, openMenu })

  useEffect(() => {
    if (enabled) return
    closeMenu()
  }, [closeMenu, enabled])

  return {
    isOpen: menuState.isOpen,
    positionReference: menuState.positionReference,
    selectedText: menuState.selectedText,
    actionContext: menuState.actionContext,
    handleContextMenu,
    onOpenChange,
  }
}

function useDesktopContextMenu({ enabled, openMenu }) {
  return useCallback((event) => {
    console.log('[ctxmenu] handleContextMenu — enabled:', enabled, '| target:', event.target.tagName)
    if (!enabled) return

    event.preventDefault()
    const selectionContext = readOverlaySelection()
    // `useReadingOverlayMenuActions` keys visibility off `actionContext`, so a live text selection
    // must win even inside an <a> or right-clicking linked text stops exposing `Elaborate`.
    if (selectionContext) {
      openMenu({
        source: MenuOpenSource.DESKTOP,
        positionReference: createPointPositionReference(event.clientX, event.clientY),
        selectedText: selectionContext.selectedText,
        actionContext: { kind: 'text-selection' },
      })
      return
    }

    const anchorContext = readAnchorContext(event.target)
    if (anchorContext) {
      openMenu({
        source: MenuOpenSource.LINK,
        ...anchorContext,
      })
      return
    }

    openMenu({
      source: MenuOpenSource.DESKTOP,
      positionReference: createPointPositionReference(event.clientX, event.clientY),
      selectedText: '',
      actionContext: { kind: 'text-selection' },
    })
    console.log('[ctxmenu] opened via right-click at', event.clientX, event.clientY)
  }, [enabled, openMenu])
}

function useLinkLongPressMenu({ enabled, openMenu }) {
  useEffect(() => {
    if (!enabled) return

    let longPressTimeoutId = null
    let pendingAnchorContext = null
    // Suppress only the synthetic click that belongs to the long-pressed anchor. If no such click
    // arrives, clear the latch on the next captured click so later taps do not get swallowed.
    let suppressedAnchorElement = null

    function clearLongPress() {
      window.clearTimeout(longPressTimeoutId)
      longPressTimeoutId = null
      pendingAnchorContext = null
    }

    function handlePointerDown(event) {
      if (!event.isPrimary) return
      if (event.pointerType !== 'touch' && event.pointerType !== 'pen') return

      const anchorContext = readAnchorContext(event.target)
      if (!anchorContext) return

      pendingAnchorContext = anchorContext
      longPressTimeoutId = window.setTimeout(() => {
        suppressedAnchorElement = pendingAnchorContext.anchorElement
        window.navigator.vibrate?.(8)
        openMenu({
          source: MenuOpenSource.LINK,
          ...pendingAnchorContext,
        })
        pendingAnchorContext = null
        longPressTimeoutId = null
      }, LONG_PRESS_DELAY_MS)
    }

    function handleClick(event) {
      if (!suppressedAnchorElement) return

      const anchorContext = readAnchorContext(event.target)
      if (!anchorContext || anchorContext.anchorElement !== suppressedAnchorElement) {
        suppressedAnchorElement = null
        return
      }

      event.preventDefault()
      event.stopPropagation()
      suppressedAnchorElement = null
    }

    function handlePointerMove(event) {
      if (!pendingAnchorContext) return
      if (event.pointerType !== 'touch' && event.pointerType !== 'pen') return
      clearLongPress()
    }

    document.addEventListener('pointerdown', handlePointerDown, true)
    document.addEventListener('pointerup', clearLongPress, true)
    document.addEventListener('pointercancel', clearLongPress, true)
    document.addEventListener('pointermove', handlePointerMove, true)
    document.addEventListener('click', handleClick, true)
    document.addEventListener('scroll', clearLongPress, true)

    return () => {
      clearLongPress()
      document.removeEventListener('pointerdown', handlePointerDown, true)
      document.removeEventListener('pointerup', clearLongPress, true)
      document.removeEventListener('pointercancel', clearLongPress, true)
      document.removeEventListener('pointermove', handlePointerMove, true)
      document.removeEventListener('click', handleClick, true)
      document.removeEventListener('scroll', clearLongPress, true)
    }
  }, [enabled, openMenu])
}

function useMobileSelectionMenu({ enabled, openMenu, closeMenu, resetMobileSelectionStateRef }) {
  useEffect(() => {
    if (!enabled) return
    const isTouch = matchMedia('(pointer: coarse)').matches
    console.log('[ctxmenu] mobile effect — isTouch:', isTouch)
    if (!isTouch) return

    const mobileStateRef = { current: createInitialMobileSelectionMenuState() }

    resetMobileSelectionStateRef.current = () => {
      mobileStateRef.current = createInitialMobileSelectionMenuState()
    }

    function runMobileSelectionDecision(decision) {
      if (decision.type === MobileSelectionMenuDecisionType.OPEN_MENU) {
        openMenu({
          source: MenuOpenSource.MOBILE_SELECTION,
          positionReference: decision.selection.positionReference,
          selectedText: decision.selection.selectedText,
          actionContext: { kind: 'text-selection' },
        })
        console.log('[ctxmenu] opened via selection | text:', decision.selection.selectedText.slice(0, 40))
        return
      }

      if (decision.type === MobileSelectionMenuDecisionType.CLOSE_MENU) {
        console.log('[ctxmenu] mobile reducer -> CLOSE_MENU')
        closeMenu()
      }
    }

    function dispatchMobileSelectionEvent(event) {
      const { state, decision } = reduceMobileSelectionMenu(mobileStateRef.current, event)
      mobileStateRef.current = state
      runMobileSelectionDecision(decision)
    }

    function handleTouchStart() {
      console.log('[ctxmenu] touchstart')
      dispatchMobileSelectionEvent({
        type: MobileSelectionMenuEventType.TOUCH_STARTED,
      })
    }

    function handleTouchEnd() {
      const selection = readOverlaySelection()
      console.log('[ctxmenu] touchend — selection:', selection ? selection.selectedText.slice(0, 40) : 'null')
      dispatchMobileSelectionEvent({
        type: MobileSelectionMenuEventType.TOUCH_ENDED,
        selection,
      })
    }

    function handleSelectionChange() {
      const selection = readOverlaySelection()
      console.log('[ctxmenu] selectionchange — selection:', selection ? selection.selectedText.slice(0, 40) : 'null')
      dispatchMobileSelectionEvent(selection
        ? { type: MobileSelectionMenuEventType.SELECTION_OBSERVED, selection }
        : { type: MobileSelectionMenuEventType.SELECTION_CLEARED })
    }

    document.addEventListener('touchstart', handleTouchStart, true)
    document.addEventListener('touchend', handleTouchEnd, true)
    document.addEventListener('selectionchange', handleSelectionChange)

    return () => {
      console.log('[ctxmenu] mobile cleanup')
      resetMobileSelectionStateRef.current = () => {}
      document.removeEventListener('touchstart', handleTouchStart, true)
      document.removeEventListener('touchend', handleTouchEnd, true)
      document.removeEventListener('selectionchange', handleSelectionChange)
    }
  }, [closeMenu, enabled, openMenu, resetMobileSelectionStateRef])
}
