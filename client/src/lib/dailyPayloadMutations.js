import { getCachedStorageValue, setStorageValueInMemory } from '../hooks/useSupabaseStorage'
import { getDailyPayloadWithMetadata, patchDailyArticle, patchDailyPayload } from './storageApi'
import { getNewsletterScrapeKey } from './storageKeys'

const mutationQueueByStorageKey = new Map()

function enqueueDailyPayloadMutation(storageKey, task) {
  const previousTask = mutationQueueByStorageKey.get(storageKey) || Promise.resolve()
  const nextTask = previousTask.catch(() => {}).then(task)
  mutationQueueByStorageKey.set(storageKey, nextTask)

  nextTask.finally(() => {
    if (mutationQueueByStorageKey.get(storageKey) === nextTask) {
      mutationQueueByStorageKey.delete(storageKey)
    }
  })

  return nextTask
}

function applyArticlePatchToPayload(payload, url, articlePatch) {
  if (!payload) return payload
  return {
    ...payload,
    articles: payload.articles.map((article) =>
      article.url === url ? { ...article, ...articlePatch } : article
    )
  }
}

function applyPayloadPatchToPayload(payload, payloadPatch) {
  if (!payload) return payload
  return {
    ...payload,
    ...payloadPatch
  }
}

async function loadPayloadMutationState(date, storageKey, fallbackPayload) {
  let latestPayload = getCachedStorageValue(storageKey) || fallbackPayload
  let expectedUpdatedAt = latestPayload?.storage_updated_at

  if (!expectedUpdatedAt) {
    const storageRow = await getDailyPayloadWithMetadata(date)
    if (!storageRow) throw new Error(`Daily payload not found for date: ${date}`)
    latestPayload = storageRow.payload
    expectedUpdatedAt = storageRow.updatedAt
  }

  return { latestPayload, expectedUpdatedAt }
}

async function restorePayloadInMemory(date, storageKey, fallbackPayload) {
  const storageRow = await getDailyPayloadWithMetadata(date)
  setStorageValueInMemory(storageKey, storageRow?.payload || fallbackPayload)
}

async function runQueuedOptimisticPatch({
  date,
  storageKey,
  fallbackPayload,
  applyOptimisticPayload,
  sendPatch
}) {
  return enqueueDailyPayloadMutation(storageKey, async () => {
    let { latestPayload, expectedUpdatedAt } = await loadPayloadMutationState(date, storageKey, fallbackPayload)

    for (let attemptIndex = 0; attemptIndex < 2; attemptIndex += 1) {
      const { optimisticPayload, shouldSkip } = applyOptimisticPayload(latestPayload)
      if (shouldSkip) return optimisticPayload
      setStorageValueInMemory(storageKey, optimisticPayload)

      const patchResult = await sendPatch(expectedUpdatedAt)
      if (patchResult.success) {
        setStorageValueInMemory(storageKey, patchResult.payload)
        return patchResult.payload
      }

      if (!patchResult.conflict) {
        throw new Error('Daily payload patch failed')
      }

      latestPayload = patchResult.payload
      expectedUpdatedAt = patchResult.updatedAt
    }

    throw new Error('Daily payload patch conflict retry exhausted')
  }).catch(async (error) => {
    await restorePayloadInMemory(date, storageKey, fallbackPayload)
    throw error
  })
}

export function queueDailyArticlePatch({
  date,
  url,
  patch,
  buildPatch,
  previousPayload = null,
  storageKey = getNewsletterScrapeKey(date)
}) {
  return runQueuedOptimisticPatch({
    date,
    storageKey,
    fallbackPayload: previousPayload,
    applyOptimisticPayload(latestPayload) {
      const latestArticle = latestPayload?.articles?.find((article) => article.url === url)
      if (!latestArticle) throw new Error(`Article not found for url: ${url}`)

      const resolvedPatch = typeof buildPatch === 'function' ? buildPatch(latestArticle) : patch
      if (!resolvedPatch || Object.keys(resolvedPatch).length === 0) {
        return {
          optimisticPayload: latestPayload,
          shouldSkip: true
        }
      }

      patch = resolvedPatch
      buildPatch = null
      return {
        optimisticPayload: applyArticlePatchToPayload(latestPayload, url, resolvedPatch),
        shouldSkip: false
      }
    },
    sendPatch(expectedUpdatedAt) {
      return patchDailyArticle(date, {
        url,
        patch,
        expectedUpdatedAt
      })
    }
  })
}

export function queueDailyPayloadPatch({ date, payloadPatch, previousPayload = null, storageKey = getNewsletterScrapeKey(date) }) {
  if (!payloadPatch || Object.keys(payloadPatch).length === 0) return Promise.resolve(null)

  return runQueuedOptimisticPatch({
    date,
    storageKey,
    fallbackPayload: previousPayload,
    applyOptimisticPayload(latestPayload) {
      if (!payloadPatch || Object.keys(payloadPatch).length === 0) {
        return {
          optimisticPayload: latestPayload,
          shouldSkip: true
        }
      }

      return {
        optimisticPayload: applyPayloadPatchToPayload(latestPayload, payloadPatch),
        shouldSkip: false
      }
    },
    sendPatch(expectedUpdatedAt) {
      return patchDailyPayload(date, {
        patch: payloadPatch,
        expectedUpdatedAt
      })
    }
  })
}
