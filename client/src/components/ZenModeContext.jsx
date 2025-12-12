import { createContext, useContext, useRef, useState } from 'react'

const ZenModeContext = createContext(null)

export function ZenModeProvider({ children }) {
  const [openKey, setOpenKey] = useState(null)
  const openKeyRef = useRef(null)

  const updateOpenKey = (key) => {
    openKeyRef.current = key
    setOpenKey(key)
  }

  return (
    <ZenModeContext.Provider value={{ openKey, setOpenKey: updateOpenKey, openKeyRef }}>
      {children}
    </ZenModeContext.Provider>
  )
}

export function useZenMode() {
  const context = useContext(ZenModeContext)
  if (!context) {
    throw new Error('useZenMode must be used within a ZenModeProvider')
  }
  return context
}
