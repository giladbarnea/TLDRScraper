import { useCallback, useRef, useState } from 'react'

export function useTrackedState(initialValue) {
  const [value, setValue] = useState(initialValue)
  const valueRef = useRef(value)

  const setTrackedValue = useCallback((nextValue) => {
    setValue((currentValue) => {
      const resolvedValue = typeof nextValue === 'function'
        ? nextValue(currentValue)
        : nextValue
      valueRef.current = resolvedValue
      return resolvedValue
    })
  }, [])

  return [value, setTrackedValue, valueRef]
}
