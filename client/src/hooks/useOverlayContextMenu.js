import { useCallback, useEffect, useRef, useState } from 'react'
import {
  createInitialMobileSelectionMenuState,
  MobileSelectionMenuDecisionType,
  MobileSelectionMenuEventType,
  reduceMobileSelectionMenu,
} from '../reducers/mobileSelectionMenuReducer'

const LINK_LONG_PRESS_DELAY_MS = 550
const LINK_LONG_PRESS_MOVE_TOLERANCE_PX = 10

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
  linkUrl: '',
  linkText: '',
  source: MenuOpenSource.NONE,
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
  const clientRects = Array.from(element.getClientRects()).map(copyDomRect)
  return {
    kind: 'element',
    boundingRect,
    clientRects,
    placement: 'bottom',
    offsetPx: 8,
  }
}

function getEventTargetElement(event) {
  if (event.target instanceof Element) return event.target
  return event.target.parentElement
}

function readLinkTarget(event) {
  const targetElement = getEventTargetElement(event)
  const link = targetElement?.closest('a[href]')
  if (!link || !event.currentTarget.contains(link)) return null

  return {
    linkUrl: link.href,
    linkText: link.textContent.trim() || link.href,
    positionReference: createElementPositionReference(link),
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

  const openMenu = useCallback(({ source, positionReference, selectedText = '', linkUrl = '', linkText = '' }) => {
    const nextState = {
      isOpen: true,
      positionReference,
      selectedText,
      linkUrl,
      linkText,
      source,
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
  const linkLongPressHandlers = useLinkLongPressContextMenu({ enabled, openMenu })
  useMobileSelectionMenu({ enabled, openMenu, closeMenu, resetMobileSelectionStateRef })

  useEffect(() => {
    if (enabled) return
    closeMenu()
  }, [closeMenu, enabled])

  return {
    isOpen: menuState.isOpen,
    positionReference: menuState.positionReference,
    selectedText: menuState.selectedText,
    linkUrl: menuState.linkUrl,
    linkText: menuState.linkText,
    handleContextMenu,
    linkLongPressHandlers,
    onOpenChange,
  }
}

function useDesktopContextMenu({ enabled, openMenu }) {
  return useCallback((event) => {
    console.log('[ctxmenu] handleContextMenu — enabled:', enabled, '| target:', event.target.tagName)
    if (!enabled) return

    const linkTarget = readLinkTarget(event)
    event.preventDefault()

    if (linkTarget) {
      openMenu({
        source: MenuOpenSource.LINK,
        ...linkTarget,
      })
      console.log('[ctxmenu] opened via link context menu | url:', linkTarget.linkUrl)
      return
    }

    openMenu({
      source: MenuOpenSource.DESKTOP,
      positionReference: createPointPositionReference(event.clientX, event.clientY),
      selectedText: '',
    })
    console.log('[ctxmenu] opened via right-click at', event.clientX, event.clientY)
  }, [enabled, openMenu])
}

function useLinkLongPressContextMenu({ enabled, openMenu }) {
  const timerRef = useRef(null)
  const touchStartPointRef = useRef(null)
  const didOpenRef = useRef(false)
  const suppressNextLinkClickRef = useRef(false)

  const clearTimer = useCallback(() => {
    window.clearTimeout(timerRef.current)
    timerRef.current = null
  }, [])

  const cancelPress = useCallback(() => {
    clearTimer()
    touchStartPointRef.current = null
  }, [clearTimer])

  const handleTouchStart = useCallback((event) => {
    if (!enabled) return
    const linkTarget = readLinkTarget(event)
    if (!linkTarget) return

    const touch = event.touches[0]
    didOpenRef.current = false
    touchStartPointRef.current = { x: touch.clientX, y: touch.clientY }
    clearTimer()
    timerRef.current = window.setTimeout(() => {
      didOpenRef.current = true
      suppressNextLinkClickRef.current = true
      window.navigator.vibrate?.(8)
      openMenu({
        source: MenuOpenSource.LINK,
        ...linkTarget,
      })
      console.log('[ctxmenu] opened via link long press | url:', linkTarget.linkUrl)
    }, LINK_LONG_PRESS_DELAY_MS)
  }, [clearTimer, enabled, openMenu])

  const handleTouchMove = useCallback((event) => {
    if (!touchStartPointRef.current) return
    const touch = event.touches[0]
    const deltaX = Math.abs(touch.clientX - touchStartPointRef.current.x)
    const deltaY = Math.abs(touch.clientY - touchStartPointRef.current.y)
    if (Math.max(deltaX, deltaY) <= LINK_LONG_PRESS_MOVE_TOLERANCE_PX) return
    cancelPress()
  }, [cancelPress])

  const handleTouchEnd = useCallback((event) => {
    clearTimer()
    touchStartPointRef.current = null
    if (!didOpenRef.current) return

    event.preventDefault()
    event.stopPropagation()
    window.setTimeout(() => {
      suppressNextLinkClickRef.current = false
    }, 800)
  }, [clearTimer])

  const handleClickCapture = useCallback((event) => {
    if (!suppressNextLinkClickRef.current) return
    if (!getEventTargetElement(event)?.closest('a[href]')) return

    suppressNextLinkClickRef.current = false
    event.preventDefault()
    event.stopPropagation()
  }, [])

  useEffect(() => cancelPress, [cancelPress])

  return {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd,
    onTouchCancel: cancelPress,
    onClickCapture: handleClickCapture,
  }
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

    function readOverlaySelection() {
      const selection = window.getSelection()
      const selectedText = selection?.toString().trim() ?? ''
      if (!selection || selection.isCollapsed || !selectedText) return null
      if (!selection.anchorNode?.parentElement?.closest('[data-overlay-content]')) {
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

    function runMobileSelectionDecision(decision) {
      if (decision.type === MobileSelectionMenuDecisionType.OPEN_MENU) {
        openMenu({
          source: MenuOpenSource.MOBILE_SELECTION,
          positionReference: decision.selection.positionReference,
          selectedText: decision.selection.selectedText,
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
      dispatchMobileSelectionEvent(
        selection
          ? { type: MobileSelectionMenuEventType.SELECTION_OBSERVED, selection }
          : { type: MobileSelectionMenuEventType.SELECTION_CLEARED }
      )
    }

    document.addEventListener('selectionchange', handleSelectionChange)
    document.addEventListener('touchstart', handleTouchStart, true)
    document.addEventListener('touchend', handleTouchEnd, true)

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange)
      document.removeEventListener('touchstart', handleTouchStart, true)
      document.removeEventListener('touchend', handleTouchEnd, true)
      resetMobileSelectionStateRef.current = () => {}
    }
  }, [enabled, openMenu, closeMenu, resetMobileSelectionStateRef])
}
