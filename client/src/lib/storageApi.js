async function isDateCached(date) {
  const response = await window.fetch(`/api/storage/is-cached/${date}`)
  const data = await response.json()

  if (data.success) {
    return data.is_cached
  }

  throw new Error(data.error || 'Failed to check cache')
}

async function getDailyPayload(date) {
  const response = await window.fetch(`/api/storage/daily/${date}`)
  const data = await response.json()

  if (data.success) {
    return data.payload
  }

  return null
}

export async function getDailyPayloadWithMetadata(date) {
  const response = await window.fetch(`/api/storage/daily/${date}`)
  const data = await response.json()

  if (!data.success) {
    return null
  }

  return {
    payload: data.payload,
    updatedAt: data.updated_at
  }
}

async function setDailyPayload(date, payload) {
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

export async function patchDailyArticle(date, { url, patch, expectedUpdatedAt }) {
  const response = await window.fetch(`/api/storage/daily/${date}/article`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url,
      patch,
      expected_updated_at: expectedUpdatedAt
    })
  })

  const data = await response.json()

  if (response.status === 409) {
    return {
      success: false,
      conflict: true,
      payload: data.payload,
      updatedAt: data.updated_at
    }
  }

  if (!data.success) {
    throw new Error(data.error || 'Failed to patch article')
  }

  return {
    success: true,
    payload: data.payload,
    updatedAt: data.updated_at
  }
}

export async function getDailyPayloadsRange(startDate, endDate, signal) {
  const response = await window.fetch('/api/storage/daily-range', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start_date: startDate, end_date: endDate }),
    signal
  })

  const data = await response.json()

  if (data.success) {
    return data.payloads
  }

  throw new Error(data.error || 'Failed to load payloads')
}
