import { createContext, useContext, useState } from 'react'

const ZenModeContext = createContext(null)

export function ZenModeProvider({ children }) {
  const [openKey, setOpenKey] = useState(null)
  return (
    <ZenModeContext.Provider value={{ openKey, setOpenKey }}>
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
