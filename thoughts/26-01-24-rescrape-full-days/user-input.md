currently, there's a "special case" in the scrape logic where newsletter-day's are always rescraped (no cache hit) if the scrape target day is "today". otherwise (anything but today), the first time a scrape happens the results are cached and subsequent requests return the cached data.
this is half valid rationale: it is true that if i scrape today in the morning, new articles may be published later today, so we should still scrape the sources in the evening, for example.
but this is also true for e.g. "yesterday" - if yesterday, i scraped in the morning, then didn't use the app not until the day after, yesterday is 'frozen' with whatever had been published up to morning. it's as plausible that we've missed out on new articles that were published later that day.
so:
1. we're dropping the concept of "today vs not today". the new scraping logic needs to be uniform agnostic to all days
2. a rescrape will occur for any given day as long as its last_scraped_at (epoch ts) is earlier than the western-most timezone's NEXT day's 00:00 AM. i'll explain:
let's take california time zone as "the most delayed" time globally. i even want  to capture articles that were published by someone in california at their 23:59:59 PM. so the logic is:
return cached if last_scraped_at >= roundDownTo0000am(toCaliDatetime(dayToScrape + 1 day)) else rescrape
3. for that, we also need to persist last_scraped_at when scraping
