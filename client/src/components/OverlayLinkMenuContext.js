import { createContext, useContext } from 'react'

export const OverlayLinkMenuContext = createContext(null)

export function useOverlayLinkMenu() {
  const context = useContext(OverlayLinkMenuContext)
  if (!context) throw new Error('OverlayLink must be rendered inside BaseOverlay')
  return context
}
