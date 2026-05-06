import { applyArticlePatch, applyArticlePatches, applyDayPatch, composeDayPayloadForServer, ingestDayPayload, parseArticleKey } from '../store/articleStore'
import { getDailyPayloadWithMetadata, patchDailyArticle, patchDailyPayload } from './storageApi'

const mutationQueueByDate = new Map()

function enqueueMutation(date, task) {
  const previousTask = mutationQueueByDate.get(date) || Promise.resolve()
  const nextTask = previousTask.catch(() => {}).then(task)
  mutationQueueByDate.set(date, nextTask)

  nextTask.finally(() => {
    if (mutationQueueByDate.get(date) === nextTask) {
      mutationQueueByDate.delete(date)
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

function assertUniqueKeys(items) {
  const keys = new Set()
  for (const item of items) {
    if (keys.has(item.key)) throw new Error(`Duplicate article patch for key: ${item.key}`)
    keys.add(item.key)
  }
}

function resolveArticlePatches(latestPayload, items) {
  const articlesByUrl = new Map(latestPayload.articles.map((article) => [article.url, article]))
  const resolvedItems = []

  for (const item of items) {
    const { url } = parseArticleKey(item.key)
    const latestArticle = articlesByUrl.get(url)
    if (!latestArticle) throw new Error(`Article not found for url: ${url}`)

    if (!item.resolved) {
      item.resolvedPatch = typeof item.buildPatch === 'function'
        ? item.buildPatch(latestArticle)
        : item.patch
      item.resolved = true
    }

    if (!isEmptyPatch(item.resolvedPatch)) resolvedItems.push({ ...item, url })
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

async function loadPayloadMutationState(date) {
  let latestPayload = composeDayPayloadForServer(date)
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
    ingestDayPayload(storageRow.payload)
  }
}

async function runQueuedOptimisticPatch({ date, buildOptimistic, sendPatch }) {
  return enqueueMutation(date, async () => {
    let { latestPayload, expectedUpdatedAt } = await loadPayloadMutationState(date)

    for (let attemptIndex = 0; attemptIndex < 2; attemptIndex += 1) {
      const { optimisticPayload, shouldSkip, applyOptimistic } = buildOptimistic(latestPayload)
      if (shouldSkip) return optimisticPayload

      applyOptimistic()

      const patchResult = await sendPatch(expectedUpdatedAt)
      if (patchResult.success) {
        ingestDayPayload(patchResult.payload)
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
    const { date } = parseArticleKey(item.key)
    if (!byDate.has(date)) byDate.set(date, [])
    byDate.get(date).push({ ...item, resolved: false, resolvedPatch: null })
  }

  await Promise.all([...byDate.entries()].map(([date, items]) => {
    assertUniqueKeys(items)
    let payloadPatch = null

    return runQueuedOptimisticPatch({
      date,
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
            key: item.key,
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

export function queueDailyArticlePatch({ key, patch, buildPatch }) {
  const { date, url } = parseArticleKey(key)

  return runQueuedOptimisticPatch({
    date,
    buildOptimistic(latestPayload) {
      const latestArticle = latestPayload?.articles?.find((article) => article.url === url)
      if (!latestArticle) throw new Error(`Article not found for url: ${url}`)

      const resolvedPatch = typeof buildPatch === 'function' ? buildPatch(latestArticle) : patch
      if (isEmptyPatch(resolvedPatch)) {
        return { optimisticPayload: latestPayload, shouldSkip: true, applyOptimistic: () => {} }
      }

      patch = resolvedPatch
      buildPatch = null

      return {
        optimisticPayload: applyArticlePatchToPayload(latestPayload, url, resolvedPatch),
        shouldSkip: false,
        applyOptimistic: () => applyArticlePatch(key, resolvedPatch),
      }
    },
    sendPatch(expectedUpdatedAt) {
      return patchDailyArticle(date, { url, patch, expectedUpdatedAt })
    },
  })
}

export function queueDailyPayloadPatch({ date, payloadPatch }) {
  if (isEmptyPatch(payloadPatch)) return Promise.resolve(null)

  return runQueuedOptimisticPatch({
    date,
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
