/**
 * ClientStorageModel defines the browser-owned Article/Issue schema and
 * persistence helpers for the stateless architecture.
 */

// #region -------[ ClientStorageModel ]-------

export const ARTICLE_STATUS = {
    unknown: 'unknown',
    creating: 'creating',
    available: 'available',
    error: 'error'
};

export function normalizeIsoDate(value) {
    if (typeof value !== 'string') return null;
    const trimmed = value.trim();
    if (!trimmed) return null;
    const date = new Date(trimmed);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString().split('T')[0];
}

export function getStorageKeyForDate(date) {
    return `tldr:scrapes:${date}`;
}

export function cloneArticleState(article) {
    return {
        url: article.url,
        title: article.title,
        issueDate: article.issueDate,
        category: article.category,
        section: article.section,
        sectionEmoji: article.sectionEmoji,
        sectionOrder: article.sectionOrder,
        newsletterType: article.newsletterType,
        removed: Boolean(article.removed),
        summary: {
            status: article.summary?.status || ARTICLE_STATUS.unknown,
            markdown: article.summary?.markdown || '',
            effort: article.summary?.effort || 'low',
            checkedAt: article.summary?.checkedAt || null,
            errorMessage: article.summary?.errorMessage || null
        },
        tldr: {
            status: article.tldr?.status || ARTICLE_STATUS.unknown,
            markdown: article.tldr?.markdown || '',
            effort: article.tldr?.effort || 'low',
            checkedAt: article.tldr?.checkedAt || null,
            errorMessage: article.tldr?.errorMessage || null
        },
        read: {
            isRead: Boolean(article.read?.isRead),
            markedAt: article.read?.markedAt || null
        }
    };
}

export function sanitizeIssue(issue) {
    return {
        date: normalizeIsoDate(issue.date) || null,
        category: issue.category || '',
        newsletterType: issue.newsletterType || issue.newsletter_type || null,
        title: issue.title || null,
        subtitle: issue.subtitle || null,
        sections: Array.isArray(issue.sections)
            ? issue.sections.map(section => ({
                order: section.order ?? null,
                title: section.title || null,
                emoji: section.emoji || null
            }))
            : []
    };
}

export const ClientStorage = (() => {
    function readDay(date) {
        const normalized = normalizeIsoDate(date) || date;
        const raw = localStorage.getItem(getStorageKeyForDate(normalized));
        if (!raw) return null;
        try {
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') return null;
            const issues = Array.isArray(parsed.issues) ? parsed.issues.map(sanitizeIssue) : [];
            const articles = Array.isArray(parsed.articles)
                ? parsed.articles.map(cloneArticleState)
                : [];
            return {
                date: normalized,
                cachedAt: parsed.cachedAt || new Date().toISOString(),
                issues,
                articles
            };
        } catch (error) {
            console.error('Failed to parse stored payload', error, { show: true, error: true });
            return null;
        }
    }

    function writeDay(date, payload) {
        const normalized = normalizeIsoDate(date) || date;
        const serializable = {
            date: normalized,
            cachedAt: payload.cachedAt || new Date().toISOString(),
            issues: Array.isArray(payload.issues) ? payload.issues.map(sanitizeIssue) : [],
            articles: Array.isArray(payload.articles)
                ? payload.articles.map(cloneArticleState)
                : []
        };
        localStorage.setItem(
            getStorageKeyForDate(normalized),
            JSON.stringify(serializable)
        );
        return readDay(normalized);
    }

    function mergeDay(date, payload) {
        const normalized = normalizeIsoDate(date) || date;
        const existing = readDay(normalized);
        if (!existing) {
            return writeDay(normalized, payload);
        }

        const mergedArticles = Array.isArray(payload.articles)
            ? payload.articles.map(article => {
                const prior = existing.articles.find(item => item.url === article.url);
                if (!prior) return cloneArticleState(article);
                return cloneArticleState({
                    ...article,
                    summary: { ...prior.summary, ...article.summary },
                    tldr: { ...prior.tldr, ...article.tldr },
                    read: { ...prior.read, ...article.read }
                });
            })
            : existing.articles.map(cloneArticleState);

        const mergedIssues = Array.isArray(payload.issues) && payload.issues.length
            ? payload.issues.map(sanitizeIssue)
            : existing.issues.map(sanitizeIssue);

        return writeDay(normalized, {
            cachedAt: payload.cachedAt || existing.cachedAt,
            issues: mergedIssues,
            articles: mergedArticles
        });
    }

    function hasDay(date) {
        const normalized = normalizeIsoDate(date) || date;
        return localStorage.getItem(getStorageKeyForDate(normalized)) !== null;
    }

    function updateArticle(date, url, updater) {
        const normalized = normalizeIsoDate(date) || date;
        const snapshot = readDay(normalized);
        if (!snapshot) return null;
        const index = snapshot.articles.findIndex(article => article.url === url);
        if (index === -1) return null;
        const updated = updater(cloneArticleState(snapshot.articles[index]));
        if (!updated) return null;
        snapshot.articles[index] = cloneArticleState(updated);
        return writeDay(normalized, snapshot);
    }

    return {
        readDay,
        writeDay,
        mergeDay,
        hasDay,
        updateArticle
    };
})();

// #endregion
