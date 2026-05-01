const sourceHosts = {
  tldr_tech: 'tldr.tech',
  tldr_ai: 'tldr.tech',
  hackernews: 'news.ycombinator.com',
  xeiaso: 'xeiaso.net',
  simon_willison: 'simonwillison.net',
  danluu: 'danluu.com',
  will_larson: 'lethain.com',
  pragmatic_engineer: 'newsletter.pragmaticengineer.com',
  jessitron: 'jessitron.com',
  stripe_engineering: 'stripe.com',
  deepmind: 'deepmind.google',
  google_research: 'research.google',
  pointer: 'pointer.io',
  netflix: 'medium.com',
  anthropic: 'anthropic.com',
  anthropic_news: 'anthropic.com',
  claude_blog: 'claude.com',
  softwareleadweekly: 'softwareleadweekly.com',
  hillel_wayne: 'hillelwayne.com',
  martin_fowler: 'martinfowler.com',
  react_status: 'statuscode.com',
  aiwithmike: 'aiwithmike.substack.com',
  savannah_ostrowski: 'savannah.dev',
  lucumr: 'lucumr.pocoo.org',
  trendshift: 'trendshift.io',
}

export function getSourceLogo(sourceId) {
  const hostname = sourceHosts[sourceId]
  if (!hostname) return null
  return `https://www.google.com/s2/favicons?domain=${hostname}&sz=64`
}
