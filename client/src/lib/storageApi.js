import { readApiResponse } from './apiError'

export async function getDailyPayloadWithMetadata(date) {
  const response = await window.fetch(`/api/storage/daily/${date}`)

  if (response.status === 404) {
    return null
  }

  const data = await readApiResponse(response, `GET /api/storage/daily/${date}`)

  return {
    payload: data.payload,
    updatedAt: data.updated_at
  }
}

export async function patchDailyPayload(date, { patch, expectedUpdatedAt }) {
  const response = await window.fetch(`/api/storage/daily/${date}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      patch,
      expected_updated_at: expectedUpdatedAt
    })
  })

  if (response.status === 409) {
    const conflictData = await response.json()
    return {
      success: false,
      conflict: true,
      payload: conflictData.payload,
      updatedAt: conflictData.updated_at,
    }
  }

  const data = await readApiResponse(response, `PATCH /api/storage/daily/${date}`)

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

  const data = await readApiResponse(response, 'POST /api/storage/daily-range')
  return data.payloads
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

  if (response.status === 409) {
    const conflictData = await response.json()
    return {
      success: false,
      conflict: true,
      payload: conflictData.payload,
      updatedAt: conflictData.updated_at,
    }
  }

  const data = await readApiResponse(response, `PATCH /api/storage/daily/${date}/article`)

  return {
    success: true,
    payload: data.payload,
    updatedAt: data.updated_at
  }
}
