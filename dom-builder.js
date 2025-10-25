/**
 * ClientHydration builds daily payloads, composes renderable markup, and
 * orchestrates read/write access to localStorage-backed state.
 */

import { ClientStorage, ARTICLE_STATUS, normalizeIsoDate, cloneArticleState, sanitizeIssue } from './storage.js';
import {
    parseTitleWithDomain,
    getDomainLabelFromUrl,
    setArticleLinkText,
    setCardRemovedState,
    sortArticlesByState,
    isCardRemoved,
    toggleCopyButton
} from './article-card.js';

// #region -------[ ClientHydration ]-------

export function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export function computeDateRange(startDate, endDate) {
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return [];
    }
    if (start > end) return [];
    const dates = [];
    const current = new Date(end);
    while (current >= start) {
        dates.push(current.toISOString().split('T')[0]);
        current.setDate(current.getDate() - 1);
    }
    return dates;
}

export function buildDailyPayloadsFromScrape(data) {
    const payloadByDate = new Map();
    const issuesByDate = new Map();

    if (Array.isArray(data.issues)) {
        data.issues.forEach(issue => {
            const date = normalizeIsoDate(issue.date);
            if (!date) return;
            const sanitized = sanitizeIssue(issue);
            if (!issuesByDate.has(date)) {
                issuesByDate.set(date, []);
            }
            issuesByDate.get(date).push(sanitized);
        });
    }

    if (Array.isArray(data.articles)) {
        data.articles.forEach(article => {
            const date = normalizeIsoDate(article.date);
            if (!date) return;
            const base = {
                url: article.url,
                title: article.title || article.url,
                issueDate: date,
                category: article.category || 'Newsletter',
                section: article.section_title || null,
                sectionEmoji: article.section_emoji || null,
                sectionOrder: article.section_order ?? null,
                newsletterType: article.newsletter_type || null,
                removed: Boolean(article.removed),
                summary: { status: ARTICLE_STATUS.unknown, markdown: '', effort: 'low', checkedAt: null, errorMessage: null },
                tldr: { status: ARTICLE_STATUS.unknown, markdown: '', effort: 'low', checkedAt: null, errorMessage: null },
                read: { isRead: false, markedAt: null }
            };
            if (!payloadByDate.has(date)) {
                payloadByDate.set(date, []);
            }
            payloadByDate.get(date).push(base);
        });
    }

    const payloads = [];
    payloadByDate.forEach((articles, date) => {
        const existing = ClientStorage.readDay(date);
        const mergedArticles = articles.map(article => {
            const prior = existing?.articles?.find(item => item.url === article.url);
            if (!prior) return cloneArticleState(article);
            return cloneArticleState({
                ...article,
                removed: typeof prior.removed === 'boolean' ? prior.removed : article.removed,
                summary: prior.summary,
                tldr: prior.tldr,
                read: prior.read
            });
        });
        const issues = issuesByDate.get(date) || existing?.issues || [];
        payloads.push({
            date,
            cachedAt: new Date().toISOString(),
            articles: mergedArticles,
            issues
        });
    });

    return payloads.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
}

export function buildStatsFromPayloads(payloads) {
    const uniqueUrls = new Set();
    let totalArticles = 0;
    payloads.forEach(payload => {
        payload.articles.forEach(article => {
            uniqueUrls.add(article.url);
        });
        totalArticles += payload.articles.length;
    });

    return {
        total_articles: totalArticles,
        unique_urls: uniqueUrls.size,
        dates_processed: payloads.length,
        dates_with_content: payloads.filter(payload => payload.articles.length > 0).length
    };
}

export function buildWhiteyHtmlFromPayloads(payloads) {
    const pieces = ['<main id="write">'];
    payloads.forEach(payload => {
        pieces.push(`<div class="date-header-container"><h2>${escapeHtml(payload.date)}</h2></div>`);

        const issues = (payload.issues && payload.issues.length)
            ? payload.issues
            : Array.from(new Set(payload.articles.map(article => article.category))).map(category => ({
                category,
                title: category,
                sections: []
            }));

        issues.forEach(issue => {
            const headingLabel = issue.title || issue.category || 'Newsletter';
            pieces.push(`<h4>${escapeHtml(headingLabel)}</h4>`);
            pieces.push('<ol>');

            payload.articles
                .filter(article => article.category === issue.category)
                .forEach(article => {
                    pieces.push(`<li><a href="${escapeHtml(article.url)}">${escapeHtml(article.title)}</a></li>`);
                });

            pieces.push('</ol>');
        });
    });
    pieces.push('</main>');
    return pieces.join('');
}

export function buildPayloadIndices(payloads) {
    const urlToDateMap = {};
    const urlMetaMap = new Map();
    const issueMetadataMap = new Map();

    payloads.forEach(payload => {
        payload.articles.forEach(article => {
            urlToDateMap[article.url] = payload.date;
            urlMetaMap.set(article.url, {
                title: article.title,
                section_title: article.section,
                section_emoji: article.sectionEmoji,
                section_order: article.sectionOrder,
                newsletter_type: article.newsletterType,
                removed: article.removed,
                category: article.category
            });
        });

        payload.issues.forEach(issue => {
            const key = `${payload.date}__${issue.category || ''}`;
            issueMetadataMap.set(key, {
                date: payload.date,
                category: issue.category || '',
                title: issue.title || null,
                subtitle: issue.subtitle || null,
                sections: issue.sections || [],
                newsletter_type: issue.newsletterType || issue.newsletter_type || null
            });
        });
    });

    return { urlToDateMap, urlMetaMap, issueMetadataMap };
}

function getIssueKey(dateStr, category) {
    return `${dateStr}-${category}`.toLowerCase();
}

export function transformWhiteySurface(root, maps, setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup) {
    const { urlToDateMap, urlMetaMap, issueMetadataMap } = maps;
    if (!root) return;

    root.querySelectorAll('#write h2, #write h3').forEach(function(header) {
        const container = document.createElement('div');
        container.className = 'date-header-container';

        const newHeader = header.cloneNode(true);
        container.appendChild(newHeader);

        const text = (newHeader.textContent || '').trim();
        const dateMatch = text.match(/\d{4}-\d{2}-\d{2}/);
        if (dateMatch) {
            container.setAttribute('data-date', dateMatch[0]);
        }

        header.parentNode.replaceChild(container, header);
    });

    root.querySelectorAll('#write h4').forEach(function(header) {
        const container = document.createElement('div');
        container.className = 'issue-header-container';

        let currentDate = null;
        let prevElement = header.previousElementSibling;
        while (prevElement) {
            if (prevElement.classList && prevElement.classList.contains('date-header-container')) {
                const dateHeader = prevElement.querySelector('h2, h3');
                if (dateHeader) {
                    const dateMatch = dateHeader.textContent.match(/\d{4}-\d{2}-\d{2}/);
                    if (dateMatch) {
                        currentDate = dateMatch[0];
                        break;
                    }
                }
            }
            prevElement = prevElement.previousElementSibling;
        }

        if (currentDate) {
            container.setAttribute('data-date', currentDate);
        }

        const newHeader = header.cloneNode(true);
        const categoryText = (newHeader.textContent || '').trim();
        if (categoryText) {
            container.setAttribute('data-category', categoryText);
        }

        let issueKey = null;
        if (currentDate && categoryText) {
            issueKey = getIssueKey(currentDate, categoryText);
            if (issueKey) {
                container.setAttribute('data-issue-key', issueKey);
            }
        }

        newHeader.setAttribute('data-issue-toggle', issueKey || '');
        newHeader.setAttribute('data-issue-toggle-action', 'toggle');
        newHeader.setAttribute('tabindex', '0');
        newHeader.setAttribute('aria-expanded', 'true');

        container.appendChild(newHeader);

        let issueBlock = null;
        let issueMeta = null;
        if (currentDate && categoryText) {
            issueMeta = issueMetadataMap.get(`${currentDate}__${categoryText}`) || null;
            if (issueMeta && (issueMeta.title || issueMeta.subtitle)) {
                issueBlock = document.createElement('div');
                issueBlock.className = 'issue-title-block';

                const lines = [];
                if (issueMeta.title) lines.push(issueMeta.title);
                if (issueMeta.subtitle && issueMeta.subtitle !== issueMeta.title) {
                    lines.push(issueMeta.subtitle);
                }

                lines.forEach(text => {
                    const lineEl = document.createElement('div');
                    lineEl.className = 'issue-title-line';
                    lineEl.textContent = text;
                    issueBlock.appendChild(lineEl);
                });
            }
        }

        if (issueBlock) {
            container.appendChild(issueBlock);
        }

        header.parentNode.replaceChild(container, header);
    });

    const writeRoot = root.querySelector('#write');
    if (!writeRoot) return;

    Array.from(writeRoot.querySelectorAll('.date-header-container')).forEach(function(container) {
        let node = container.nextElementSibling;
        let aiHeading = null;
        let techHeading = null;
        while (node && !(node.classList && node.classList.contains('date-header-container'))) {
            if (node.tagName === 'H4') {
                const text = (node.textContent || '').trim();
                if (!aiHeading && /TLDR\s*AI/i.test(text)) aiHeading = node;
                if (!techHeading && /TLDR\s*Tech/i.test(text)) techHeading = node;
            }
            node = node.nextElementSibling;
        }
        if (aiHeading && techHeading && (techHeading.compareDocumentPosition(aiHeading) & Node.DOCUMENT_POSITION_FOLLOWING)) {
            const aiList = (aiHeading.nextElementSibling && aiHeading.nextElementSibling.tagName === 'OL') ? aiHeading.nextElementSibling : null;
            container.parentNode.insertBefore(aiHeading, techHeading);
            if (aiList) container.parentNode.insertBefore(aiList, techHeading);
        }
    });

    root.querySelectorAll('#write ol').forEach(function(ol) {
        const articleList = document.createElement('div');
        articleList.className = 'article-list';

        const listItems = ol.querySelectorAll('li');
        let lastSectionKey = null;
        let insertedSectionTitle = false;

        listItems.forEach(function(li, index) {
            const link = li.querySelector('a[href]');
            if (!link) return;

            const card = document.createElement('div');
            const urlValue = link.getAttribute('href');
            const titleText = link.textContent.trim();

            const cleanUrl = urlValue.replace('?data-removed=true', '');

            const articleMeta = urlMetaMap.get(cleanUrl);
            const titleParts = parseTitleWithDomain(titleText);
            const originalTitle = (articleMeta && articleMeta.title) || titleParts.title || titleText;
            card.setAttribute('data-original-title', originalTitle);
            const domainLabel = titleParts.domain || getDomainLabelFromUrl(cleanUrl);
            if (domainLabel) {
                card.setAttribute('data-domain-label', domainLabel);
            }
            let sectionKey = null;
            if (articleMeta && articleMeta.section_title) {
                const sectionOrder = articleMeta.section_order ?? '';
                sectionKey = `${sectionOrder}__${articleMeta.section_title}`;
                if (sectionKey !== lastSectionKey) {
                    const labelParts = [];
                    if (articleMeta.section_emoji) {
                        labelParts.push(articleMeta.section_emoji);
                    }
                    labelParts.push(articleMeta.section_title);
                    const sectionLabel = labelParts.join(' ').trim();
                    if (sectionLabel) {
                        const sectionEl = document.createElement('div');
                        sectionEl.className = 'section-title';
                        sectionEl.textContent = sectionLabel;
                        articleList.appendChild(sectionEl);
                        lastSectionKey = sectionKey;
                        insertedSectionTitle = true;
                    }
                }
            } else if (lastSectionKey !== null) {
                lastSectionKey = null;
            }

            card.className = 'article-card unread';
            card.setAttribute('data-url', cleanUrl);
            card.setAttribute('data-title', titleText);
            card.setAttribute('data-original-order', String(index));

            if (articleMeta && articleMeta.section_title) {
                card.setAttribute('data-section-title', articleMeta.section_title);
                if (articleMeta.section_emoji) {
                    card.setAttribute('data-section-emoji', articleMeta.section_emoji);
                }
                if (articleMeta.section_order !== undefined && articleMeta.section_order !== null) {
                    card.setAttribute('data-section-order', String(articleMeta.section_order));
                }
            }
            if (articleMeta && articleMeta.newsletter_type) {
                card.setAttribute('data-newsletter-type', articleMeta.newsletter_type);
            }

            const articleDate = urlToDateMap[cleanUrl];
            if (articleDate) {
                card.setAttribute('data-date', articleDate);
            }

            const header = document.createElement('div');
            header.className = 'article-header';

            const number = document.createElement('div');
            number.className = 'article-number';
            number.textContent = index + 1;

            const content = document.createElement('div');
            content.className = 'article-content';

            const newLink = link.cloneNode(true);
            newLink.className = 'article-link';
            newLink.setAttribute('target', '_blank');
            newLink.setAttribute('rel', 'noopener noreferrer');
            newLink.setAttribute('data-url', cleanUrl);
            newLink.setAttribute('href', cleanUrl);
            newLink.textContent = '';

            let faviconUrl = '';
            try {
                const parsedUrl = new URL(cleanUrl);
                faviconUrl = `${parsedUrl.origin}/favicon.ico`;
            } catch (err) {
                faviconUrl = '';
            }

            if (faviconUrl) {
                const favicon = document.createElement('img');
                favicon.className = 'article-favicon';
                favicon.setAttribute('loading', 'lazy');
                favicon.setAttribute('alt', '');
                favicon.src = faviconUrl;
                const space = document.createTextNode(' ');
                favicon.addEventListener('error', () => {
                    space.remove();
                    favicon.remove();
                });
                newLink.appendChild(favicon);
                newLink.appendChild(space);
            }

            const linkTextSpan = document.createElement('span');
            linkTextSpan.className = 'article-link-text';
            newLink.appendChild(linkTextSpan);
            setArticleLinkText(newLink, titleText);

            const actions = document.createElement('div');
            actions.className = 'article-actions';

            const expandBtnContainer = document.createElement('div');
            expandBtnContainer.className = 'expand-btn-container';

            const expandBtn = document.createElement('button');
            expandBtn.className = 'article-btn expand-btn collapsed-state';
            expandBtn.innerHTML = 'Summarize';
            expandBtn.title = 'Show summary with default reasoning effort';
            expandBtn.setAttribute('data-url', cleanUrl);
            expandBtn.type = 'button';

            const chevronBtn = document.createElement('button');
            chevronBtn.className = 'article-btn expand-chevron-btn';
            chevronBtn.innerHTML = '▾';
            chevronBtn.title = 'Choose reasoning effort level';
            chevronBtn.type = 'button';

            const dropdown = document.createElement('div');
            dropdown.className = 'effort-dropdown';

            SUMMARY_EFFORT_OPTIONS.forEach((option) => {
                const item = document.createElement('button');
                item.className = 'effort-dropdown-item';
                item.type = 'button';
                item.setAttribute('data-effort', option.value);

                const label = document.createElement('span');
                label.className = 'effort-label';
                label.textContent = option.label;

                item.appendChild(label);
                dropdown.appendChild(item);
            });

            expandBtnContainer.appendChild(expandBtn);
            expandBtnContainer.appendChild(chevronBtn);
            expandBtnContainer.appendChild(dropdown);

            const tldrBtn = document.createElement('button');
            tldrBtn.className = 'article-btn tldr-btn collapsed-state';
            tldrBtn.innerHTML = 'TLDR';
            tldrBtn.title = 'Show TLDR';
            tldrBtn.setAttribute('data-url', cleanUrl);
            tldrBtn.type = 'button';

            const copyBtn = document.createElement('button');
            copyBtn.className = 'article-btn copy-summary-btn';
            copyBtn.innerHTML = clipboardIconMarkup;
            copyBtn.title = 'Copy summary';
            copyBtn.type = 'button';
            copyBtn.setAttribute('data-url', cleanUrl);

            const removeBtn = document.createElement('button');
            removeBtn.className = 'article-btn remove-article-btn';
            removeBtn.innerHTML = 'Remove';
            removeBtn.title = 'Remove this article from the list';
            removeBtn.type = 'button';
            removeBtn.setAttribute('data-url', cleanUrl);

            content.appendChild(newLink);
            header.appendChild(number);
            header.appendChild(content);

            header.appendChild(actions);
            actions.appendChild(expandBtnContainer);
            actions.appendChild(tldrBtn);
            actions.appendChild(copyBtn);
            actions.appendChild(removeBtn);

            setCardSummaryEffort(card, 'low');
            setupSummaryEffortControls(card, expandBtn, chevronBtn, dropdown);

            card.appendChild(header);

            const removedNote = document.createElement('div');
            removedNote.className = 'article-removed-note';
            card.appendChild(removedNote);

            articleList.appendChild(card);

            const initialRemoved = Boolean(articleMeta && articleMeta.removed);
            setCardRemovedState(card, initialRemoved);
        });

        sortArticlesByState(articleList);

        ol.parentNode.replaceChild(articleList, ol);

        if (insertedSectionTitle) {
            let prevNode = articleList.previousElementSibling;
            while (prevNode) {
                if (prevNode.tagName === 'H5') {
                    const nodeToRemove = prevNode;
                    prevNode = prevNode.previousElementSibling;
                    nodeToRemove.remove();
                    continue;
                }
                if (prevNode.tagName === 'P' && !(prevNode.textContent || '').trim()) {
                    const nodeToRemove = prevNode;
                    prevNode = prevNode.previousElementSibling;
                    nodeToRemove.remove();
                    continue;
                }
                break;
            }
        }

    });
}

function setCardSummaryEffort(card, value) {
    if (!card) return;
    card.setAttribute('data-summary-effort', value);
}

export function renderPayloads(payloads, options, setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup) {
    const result = document.getElementById('result');
    if (!result) return;

    if (!payloads.length) {
        result.innerHTML = '<div class="empty-result">No cached newsletters found for the selected range.</div>';
        result.style.display = 'block';
        return;
    }

    const stats = options.stats || buildStatsFromPayloads(payloads);
    const statsLines = [`📊 Stats: ${stats.total_articles} articles, ${stats.unique_urls} unique URLs`,
        `📅 Dates: ${stats.dates_with_content}/${stats.dates_processed} with content`];
    if (options.source) {
        statsLines.push(`Source: ${escapeHtml(options.source)}`);
    }
    const statsHtml = `<div class="stats">${statsLines.join('<br>')}</div>`;

    const whiteyHtml = buildWhiteyHtmlFromPayloads(payloads);
    result.innerHTML = statsHtml + '<div id="logs-slot"></div>' + whiteyHtml;
    result.style.display = 'block';

    const { urlToDateMap, urlMetaMap, issueMetadataMap } = buildPayloadIndices(payloads);
    transformWhiteySurface(result, { urlToDateMap, urlMetaMap, issueMetadataMap }, setupSummaryEffortControls, SUMMARY_EFFORT_OPTIONS, clipboardIconMarkup);
    applyStoredArticleState(payloads);
}

export function hydrateRangeFromStore(startDate, endDate) {
    const dates = computeDateRange(startDate, endDate);
    const payloads = [];
    dates.forEach(date => {
        const payload = ClientStorage.readDay(date);
        if (payload) {
            payloads.push(payload);
        }
    });
    return payloads;
}

export function applyStoredArticleState(payloads) {
    const cssEscape = (value) => {
        if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
            return CSS.escape(value);
        }
        return String(value).replace(/(["'\\\s])/g, '\\$1');
    };

    const applySummaryState = (card, summary) => {
        const expandBtn = card.querySelector('.expand-btn');
        if (!expandBtn) return;

        expandBtn.disabled = false;
        expandBtn.classList.remove('error');
        card.removeAttribute('data-summary-error');

        if (summary?.status === ARTICLE_STATUS.available && summary.markdown) {
            card.setAttribute('data-summary', summary.markdown);
            expandBtn.classList.add('loaded');
            if (!expandBtn.classList.contains('expanded')) {
                expandBtn.innerHTML = 'Available';
                expandBtn.title = 'Summary cached - click to show';
                expandBtn.classList.remove('collapsed-state');
            }
            toggleCopyButton(card, true);
            return;
        }

        if (summary?.status === ARTICLE_STATUS.creating) {
            expandBtn.disabled = true;
            expandBtn.innerHTML = 'Loading...';
            expandBtn.title = 'Loading summary...';
            expandBtn.classList.remove('loaded');
            toggleCopyButton(card, false);
            return;
        }

        if (summary?.status === ARTICLE_STATUS.error) {
            card.removeAttribute('data-summary');
            card.setAttribute('data-summary-error', summary.errorMessage || 'Summary failed');
            expandBtn.classList.remove('loaded');
            expandBtn.innerHTML = 'Retry';
            expandBtn.title = summary.errorMessage ? `Error: ${summary.errorMessage}` : 'Retry summary';
            expandBtn.classList.add('collapsed-state');
            toggleCopyButton(card, false);
            return;
        }

        card.removeAttribute('data-summary');
        expandBtn.classList.remove('loaded');
        expandBtn.innerHTML = 'Summarize';
        expandBtn.title = 'Show summary with default reasoning effort';
        expandBtn.classList.add('collapsed-state');
        toggleCopyButton(card, false);
    };

    const applyTldrState = (card, tldr) => {
        const tldrBtn = card.querySelector('.tldr-btn');
        if (!tldrBtn) return;

        tldrBtn.disabled = false;
        tldrBtn.classList.remove('error');
        card.removeAttribute('data-tldr-error');

        if (tldr?.status === ARTICLE_STATUS.available && tldr.markdown) {
            card.setAttribute('data-tldr', tldr.markdown);
            if (!tldrBtn.classList.contains('expanded')) {
                tldrBtn.innerHTML = 'Available';
                tldrBtn.title = 'TLDR cached - click to show';
                tldrBtn.classList.add('loaded');
                tldrBtn.classList.remove('collapsed-state');
            }
            return;
        }

        if (tldr?.status === ARTICLE_STATUS.creating) {
            tldrBtn.disabled = true;
            tldrBtn.innerHTML = 'Loading...';
            tldrBtn.title = 'Loading TLDR...';
            tldrBtn.classList.remove('loaded');
            tldrBtn.classList.add('collapsed-state');
            return;
        }

        if (tldr?.status === ARTICLE_STATUS.error) {
            card.removeAttribute('data-tldr');
            card.setAttribute('data-tldr-error', tldr.errorMessage || 'TLDR failed');
            tldrBtn.innerHTML = 'Retry';
            tldrBtn.title = tldr.errorMessage ? `Error: ${tldr.errorMessage}` : 'Retry TLDR';
            tldrBtn.classList.remove('loaded');
            tldrBtn.classList.add('collapsed-state');
            return;
        }

        card.removeAttribute('data-tldr');
        tldrBtn.innerHTML = 'TLDR';
        tldrBtn.title = 'Show TLDR';
        tldrBtn.classList.remove('loaded');
        tldrBtn.classList.add('collapsed-state');
    };

    payloads.forEach(payload => {
        payload.articles.forEach(article => {
            const selector = `.article-card[data-date="${payload.date}"][data-url="${cssEscape(article.url)}"]`;
            const card = document.querySelector(selector);
            if (!card) return;

            if (article.read?.isRead) {
                card.classList.remove('unread');
                card.classList.add('read');
            } else {
                card.classList.remove('read');
                card.classList.add('unread');
            }

            applySummaryState(card, article.summary);
            applyTldrState(card, article.tldr);

            const removed = Boolean(article.removed);
            setCardRemovedState(card, removed);
        });
    });
}

// #endregion
