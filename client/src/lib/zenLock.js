let zenLockOwner = null

export function acquireZenLock(owner) {
  if (zenLockOwner === null) {
    zenLockOwner = owner
    return true
  }
  return false
}

export function releaseZenLock(owner) {
  if (zenLockOwner === owner) {
    zenLockOwner = null
  }
}
