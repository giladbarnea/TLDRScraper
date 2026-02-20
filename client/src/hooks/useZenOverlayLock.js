let zenOverlayLockOwner = null

export function acquireZenOverlayLock(ownerId) {
  if (zenOverlayLockOwner === null) {
    zenOverlayLockOwner = ownerId
    return true
  }
  return false
}

export function releaseZenOverlayLock(ownerId) {
  if (zenOverlayLockOwner === ownerId) {
    zenOverlayLockOwner = null
  }
}
