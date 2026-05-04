import { applyArticlePatch, applyArticlePatches, applyDayPatch, composePayloadFromStore, replaceDayFromServer } from '../store/articleStore'
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
    ),
  }
}

function applyPayloadPatchToPayload(payload, payloadPatch) {
  if (!payload) return payload
  return { ...payload, ...payloadPatch }
}

function isEmptyPatch(patch) {
  return !patch || Object.keys(patch).length === 0
}

function assertUniqueUrls(items) {
  const urls = new Set()
  for (const item of items) {
    if (urls.has(item.url)) throw new Error(`Duplicate article patch for url: ${item.url}`)
    urls.add(item.url)
  }
}

function resolveArticlePatches(latestPayload, items) {
  const articlesByUrl = new Map(latestPayload.articles.map((article) => [article.url, article]))
  const resolvedItems = []

  for (const item of items) {
    const latestArticle = articlesByUrl.get(item.url)
    if (!latestArticle) throw new Error(`Article not found for url: ${item.url}`)

    if (!item.resolved) {
      item.resolvedPatch = typeof item.buildPatch === 'function'
        ? item.buildPatch(latestArticle)
        : item.patch
      item.resolved = true
    }

    if (!isEmptyPatch(item.resolvedPatch)) resolvedItems.push(item)
  }

  return resolvedItems
}

function applyArticlePatchesToPayload(payload, resolvedItems) {
  const patchByUrl = new Map(resolvedItems.map((item) => [item.url, item.resolvedPatch]))

  return {
    ...payload,
    articles: payload.articles.map((article) => {
      const articlePatch = patchByUrl.get(article.url)
      return articlePatch ? { ...article, ...articlePatch } : article
    }),
  }
}

async function loadPayloadMutationState(date, fallbackPayload) {
  // Possibly a true positive: reveals a potential minor queue-key vs state-key mismatch.
  let latestPayload = composePayloadFromStore(date) || fallbackPayload
  let expectedUpdatedAt = latestPayload?.storage_updated_at

  if (!expectedUpdatedAt) {
    const storageRow = await getDailyPayloadWithMetadata(date)
    if (!storageRow) throw new Error(`Daily payload not found for date: ${date}`)
    latestPayload = storageRow.payload
    expectedUpdatedAt = storageRow.updatedAt
  }

  return { latestPayload, expectedUpdatedAt }
}

async function restorePayloadFromServer(date) {
  const storageRow = await getDailyPayloadWithMetadata(date)
  if (storageRow?.payload) {
    replaceDayFromServer(date, storageRow.payload)
  }
}

async function runQueuedOptimisticPatch({
  date,
  storageKey,
  fallbackPayload,
  // Returns { optimisticPayload, shouldSkip, applyOptimistic }
  // applyOptimistic(resolvedPatch) applies to store; called only when !shouldSkip
  buildOptimistic,
  sendPatch,
}) {
  return enqueueDailyPayloadMutation(storageKey, async () => {
    let { latestPayload, expectedUpdatedAt } = await loadPayloadMutationState(date, fallbackPayload)

    for (let attemptIndex = 0; attemptIndex < 2; attemptIndex += 1) {
      const { optimisticPayload, shouldSkip, applyOptimistic } = buildOptimistic(latestPayload)
      if (shouldSkip) return optimisticPayload

      applyOptimistic()

      const patchResult = await sendPatch(expectedUpdatedAt)
      if (patchResult.success) {
        replaceDayFromServer(date, patchResult.payload)
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
    await restorePayloadFromServer(date)
    throw error
  })
}

export async function queueBatchArticlePatches(patches) {
  const byDate = new Map()
  for (const item of patches) {
    if (!byDate.has(item.date)) byDate.set(item.date, [])
    byDate.get(item.date).push({ ...item, resolved: false, resolvedPatch: null })
  }

  await Promise.all([...byDate.entries()].map(([date, items]) => {
    assertUniqueUrls(items)
    const storageKey = items[0]?.storageKey ?? getNewsletterScrapeKey(date)
    let payloadPatch = null

    return runQueuedOptimisticPatch({
      date,
      storageKey,
      fallbackPayload: null,
      buildOptimistic(latestPayload) {
        const resolvedItems = resolveArticlePatches(latestPayload, items)
        if (resolvedItems.length === 0) {
          return { optimisticPayload: latestPayload, shouldSkip: true, applyOptimistic: () => {} }
        }

        const optimisticPayload = applyArticlePatchesToPayload(latestPayload, resolvedItems)
        payloadPatch = { articles: optimisticPayload.articles }

        return {
          optimisticPayload,
          shouldSkip: false,
          applyOptimistic: () => applyArticlePatches(resolvedItems.map((item) => ({
            key: `${date}::${item.url}`,
            patch: item.resolvedPatch,
          }))),
        }
      },
      sendPatch(expectedUpdatedAt) {
        return patchDailyPayload(date, { patch: payloadPatch, expectedUpdatedAt })
      },
    })
  }))
}

export function queueDailyArticlePatch({
  date,
  url,
  patch,
  buildPatch,
  previousPayload = null,
  storageKey = getNewsletterScrapeKey(date),
}) {
  const articleKey = `${date}::${url}`

  return runQueuedOptimisticPatch({
    date,
    storageKey,
    fallbackPayload: previousPayload,
    buildOptimistic(latestPayload) {
      const latestArticle = latestPayload?.articles?.find((article) => article.url === url)
      if (!latestArticle) throw new Error(`Article not found for url: ${url}`)

      const resolvedPatch = typeof buildPatch === 'function' ? buildPatch(latestArticle) : patch
      if (isEmptyPatch(resolvedPatch)) {
        return { optimisticPayload: latestPayload, shouldSkip: true, applyOptimistic: () => {} }
      }

      // Freeze the resolved patch — must not re-evaluate buildPatch on retry
      patch = resolvedPatch
      buildPatch = null

      return {
        optimisticPayload: applyArticlePatchToPayload(latestPayload, url, resolvedPatch),
        shouldSkip: false,
        applyOptimistic: () => applyArticlePatch(articleKey, resolvedPatch),
      }
    },
    sendPatch(expectedUpdatedAt) {
      return patchDailyArticle(date, { url, patch, expectedUpdatedAt })
    },
  })
}

export function queueDailyPayloadPatch({
  date,
  payloadPatch,
  previousPayload = null,
  storageKey = getNewsletterScrapeKey(date),
}) {
  if (isEmptyPatch(payloadPatch)) return Promise.resolve(null)

  return runQueuedOptimisticPatch({
    date,
    storageKey,
    fallbackPayload: previousPayload,
    buildOptimistic(latestPayload) {
      if (isEmptyPatch(payloadPatch)) {
        return { optimisticPayload: latestPayload, shouldSkip: true, applyOptimistic: () => {} }
      }
      return {
        optimisticPayload: applyPayloadPatchToPayload(latestPayload, payloadPatch),
        shouldSkip: false,
        applyOptimistic: () => applyDayPatch(date, payloadPatch),
      }
    },
    sendPatch(expectedUpdatedAt) {
      return patchDailyPayload(date, { patch: payloadPatch, expectedUpdatedAt })
    },
  })
}
