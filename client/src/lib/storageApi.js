export async function isDateCached(date) {
  const response = await window.fetch(`/api/storage/is-cached/${date}`)
  const data = await response.json()

  if (data.success) {
    return data.is_cached
  }

  throw new Error(data.error || 'Failed to check cache')
}

export async function getDailyPayload(date) {
  const response = await window.fetch(`/api/storage/daily/${date}`)
  const data = await response.json()

  if (data.success) {
    return data.payload
  }

  return null
}

export async function setDailyPayload(date, payload) {
  const response = await window.fetch(`/api/storage/daily/${date}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload })
  })

  const data = await response.json()

  if (!data.success) {
    throw new Error(data.error || 'Failed to save payload')
  }

  return data.data
}

export async function getDailyPayloadsRange(startDate, endDate) {
  const response = await window.fetch('/api/storage/daily-range', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start_date: startDate, end_date: endDate })
  })

  const data = await response.json()

  if (data.success) {
    return data.payloads
  }

  throw new Error(data.error || 'Failed to load payloads')
}
