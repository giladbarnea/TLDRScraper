import { motion } from 'framer-motion'
import { useAllArticlesRemoved } from '../store/articleStore'

function RemovedOrderSlot({ date, urls, originalOrder, children, className = '' }) {
  const allRemoved = useAllArticlesRemoved(date, urls)
  const order = allRemoved ? 10_000 + originalOrder : originalOrder

  return (
    <motion.div layout style={{ order }} className={className}>
      {children(allRemoved)}
    </motion.div>
  )
}

export default RemovedOrderSlot
