const subscribers = new Set()

export function emitToast(toast) {
  for (const callback of subscribers) {
    callback(toast)
  }
}

export function subscribeToToasts(callback) {
  subscribers.add(callback)
  return () => subscribers.delete(callback)
}
