const subscribersByUrl = new Map()

function getSubscribers(url) {
  if (!subscribersByUrl.has(url)) {
    subscribersByUrl.set(url, new Set())
  }
  return subscribersByUrl.get(url)
}

export function subscribeToArticleAction(url, callback) {
  const subscribers = getSubscribers(url)
  subscribers.add(callback)
  return () => {
    subscribers.delete(callback)
    if (subscribers.size === 0) {
      subscribersByUrl.delete(url)
    }
  }
}

export function publishArticleAction(urls, action) {
  for (const url of urls) {
    const subscribers = subscribersByUrl.get(url)
    if (!subscribers) continue
    for (const callback of subscribers) {
      callback(action)
    }
  }
}
