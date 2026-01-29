import { useCallback } from 'react'
import { useSelection } from '../contexts/SelectionContext'
import { useLongPress } from '../hooks/useLongPress'

function SelectionTrigger({ articleIds, children }) {
  const { isSelectMode, selectMany, deselectMany, isSelected } = useSelection()

  const handleSelect = useCallback(() => {
    const allSelected = articleIds.length > 0 && articleIds.every(id => isSelected(id))
    if (allSelected) {
      deselectMany(articleIds)
    } else {
      selectMany(articleIds)
    }
  }, [articleIds, isSelected, selectMany, deselectMany])

  const longPress = useLongPress(handleSelect)

  const handleClickCapture = useCallback((e) => {
    if (longPress.isLongPressRef.current) {
      e.stopPropagation()
      e.preventDefault()
      return
    }

    if (isSelectMode) {
      e.stopPropagation()
      e.preventDefault()
      handleSelect()
    }
  }, [isSelectMode, handleSelect, longPress.isLongPressRef])

  return (
    <div onClickCapture={handleClickCapture} {...longPress}>
      {children}
    </div>
  )
}

export default SelectionTrigger
