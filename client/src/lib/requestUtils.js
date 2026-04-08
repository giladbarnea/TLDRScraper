export function createRequestToken() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}
