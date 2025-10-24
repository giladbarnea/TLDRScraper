/**
 * Issue-level operations (collapse/expand and read state)
 */

// #region -------[ IssueCollapseManager ]-------

export function escapeIssueKeySelector(issueKey) {
    if (typeof issueKey !== 'string') return issueKey;
    if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
        return CSS.escape(issueKey);
    }
    return issueKey.replace(/(["'\\])/g, '\\$1');
}

export function findIssueContainer(issueKey, toggleEl) {
    if (issueKey) {
        const escapedKey = escapeIssueKeySelector(issueKey);
        const container = document.querySelector(`.issue-header-container[data-issue-key="${escapedKey}"]`);
        if (container) return container;
    }
    if (toggleEl) {
        const container = toggleEl.closest('.issue-header-container');
        if (container) return container;
    }
    return null;
}

export function getIssueContentNodes(container) {
    if (!container) return [];
    const nodes = [];
    let node = container.nextElementSibling;
    while (node && !node.classList.contains('issue-header-container') && !node.classList.contains('date-header-container')) {
        nodes.push(node);
        node = node.nextElementSibling;
    }
    return nodes;
}

export function collapseIssueContent(container, options = {}) {
    if (!container) return;
    const mode = options.mode || 'in-place';
    const currentMode = container.getAttribute('data-collapse-mode');
    if (currentMode === mode) return;
    if (currentMode === 'marked-read' && mode !== 'marked-read') return;

    const nodes = getIssueContentNodes(container);
    nodes.forEach(node => {
        if (node.dataset.issueDisplay === undefined) {
            node.dataset.issueDisplay = node.style.display || '';
        }
        node.style.display = 'none';
        node.setAttribute('data-collapsed', 'true');
    });

    container.setAttribute('data-collapsed', 'true');
    container.setAttribute('data-collapse-mode', mode);

    const header = container.querySelector('h4[data-issue-toggle]');
    if (header) {
        header.setAttribute('aria-expanded', 'false');
    }
}

export function expandIssueContent(container) {
    if (!container) return;
    if (container.getAttribute('data-collapse-mode') !== 'in-place') return;

    const nodes = getIssueContentNodes(container);
    nodes.forEach(node => {
        if (node.dataset.issueDisplay !== undefined) {
            node.style.display = node.dataset.issueDisplay;
            delete node.dataset.issueDisplay;
        } else {
            node.style.removeProperty('display');
        }
        node.removeAttribute('data-collapsed');
    });

    container.removeAttribute('data-collapsed');
    container.removeAttribute('data-collapse-mode');

    const header = container.querySelector('h4[data-issue-toggle]');
    if (header) {
        header.setAttribute('aria-expanded', 'true');
    }
}

export function toggleIssueContent(container) {
    if (!container) return;
    const mode = container.getAttribute('data-collapse-mode');
    if (mode === 'marked-read') return;
    if (mode === 'in-place') {
        expandIssueContent(container);
        return;
    }
    collapseIssueContent(container, { mode: 'in-place' });
}

// #endregion

// #region -------[ IssueDayReadState ]-------

const READ_STATE_KEY = 'tldr-read-issues';

export function getReadIssues() {
    try {
        const stored = localStorage.getItem(READ_STATE_KEY);
        return stored ? JSON.parse(stored) : {};
    } catch {
        return {};
    }
}

export function setIssueRead(issueKey, isRead) {
    const readIssues = getReadIssues();
    if (isRead) {
        readIssues[issueKey] = true;
    } else {
        delete readIssues[issueKey];
    }
    localStorage.setItem(READ_STATE_KEY, JSON.stringify(readIssues));
}

export function isIssueRead(issueKey) {
    return getReadIssues()[issueKey] === true;
}

export function getIssueKey(dateStr, category) {
    return `${dateStr}-${category}`.toLowerCase();
}

export function markIssueAsRead(container) {
    try {
        console.log('markIssueAsRead called', {show: true});

        if (!container || container.getAttribute('data-collapse-mode') === 'marked-read') {
            console.log('Issue already marked as read or container missing', {show: true});
            return;
        }

        const header = container.querySelector('h4');
        if (!header) {
            console.error('No h4 found in container', {show: true});
            return;
        }

        const headerText = header.textContent.trim();
        console.log('Header text:', headerText, {show: true});

        const date = container.getAttribute('data-date');
        if (!date) {
            console.error('No data-date attribute found on container', {show: true});
            return;
        }
        console.log('Date:', date, {show: true});

        const category = headerText.includes('AI') ? 'AI' : 'Tech';
        const issueKey = getIssueKey(date, category);
        console.log('Issue key:', issueKey, {show: true});

        const collapsedSection = ensureCollapsedSection();
        const issueContent = extractIssueContent(container);

        const collapsedIssue = document.createElement('div');
        collapsedIssue.className = 'collapsed-issue';
        collapsedIssue.setAttribute('data-issue-key', issueKey);

        const headerContainer = document.createElement('div');
        headerContainer.className = 'collapsed-issue-header';

        const title = document.createElement('div');
        title.className = 'collapsed-issue-title';
        title.textContent = headerText + ' – ' + date;

        const markReadBtn = document.createElement('button');
        markReadBtn.className = 'mark-read-btn';
        markReadBtn.textContent = 'Mark as Read';
        markReadBtn.title = 'Collapse and move to bottom';
        markReadBtn.type = 'button';
        markReadBtn.setAttribute('data-issue-toggle-action', 'mark-read');
        markReadBtn.setAttribute('data-issue-toggle', issueKey || '');

        headerContainer.appendChild(title);
        headerContainer.appendChild(markReadBtn);

        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'collapsed-issue-content';
        contentWrapper.appendChild(issueContent);

        collapsedIssue.appendChild(headerContainer);
        collapsedIssue.appendChild(contentWrapper);

        collapsedSection.appendChild(collapsedIssue);

        collapseIssueContent(container, { mode: 'marked-read' });
        container.style.display = 'none';

        setIssueRead(issueKey, true);
        console.log('Issue marked as read successfully', {show: true});
    } catch (error) {
        console.error('Error in markIssueAsRead:', error, {show: true});
    }
}

function extractIssueContent(container) {
    const content = document.createElement('div');
    const nodes = getIssueContentNodes(container);
    nodes.forEach(node => {
        content.appendChild(node.cloneNode(true));
    });
    return content;
}

function ensureCollapsedSection() {
    let section = document.querySelector('.collapsed-issues-section');
    if (!section) {
        const writeRoot = document.querySelector('#write');
        if (writeRoot) {
            section = document.createElement('div');
            section.className = 'collapsed-issues-section';

            const heading = document.createElement('h3');
            heading.textContent = 'Read Issues';
            section.appendChild(heading);

            writeRoot.appendChild(section);
        }
    }
    return section;
}

export function bindCollapsedIssueClick() {
    document.addEventListener('click', function(e) {
        if (e.target.closest('button')) return;
        if (e.target.closest('a')) return;
        if (e.target.closest('.collapsed-issue-content')) return;

        const titleEl = e.target.closest('.collapsed-issue-title');
        if (!titleEl) return;

        const collapsedIssue = titleEl.closest('.collapsed-issue');
        if (!collapsedIssue) return;

        collapsedIssue.classList.toggle('expanded');
    });
}

export function bindIssueToggleControls() {
    function handleIssueToggle(element, event) {
        const action = element.getAttribute('data-issue-toggle-action') || 'toggle';
        const issueKey = element.getAttribute('data-issue-toggle');
        const issueContainer = findIssueContainer(issueKey, element);

        if (action === 'toggle') {
            event.preventDefault();
            event.stopPropagation();
            if (!issueContainer) return;
            toggleIssueContent(issueContainer);
            return;
        }

        if (action === 'mark-read') {
            event.preventDefault();
            event.stopPropagation();

            const collapsedIssue = element.closest('.collapsed-issue');

            if (issueContainer && issueContainer.getAttribute('data-collapse-mode') !== 'marked-read') {
                console.log('Marking issue as read from header:', issueContainer);
                markIssueAsRead(issueContainer);
                return;
            }

            if (collapsedIssue) {
                console.log('Collapsing expanded read issue', {show: true});
                collapsedIssue.classList.remove('expanded');
                return;
            }

            if (issueContainer) {
                console.log('Mark as read clicked but issue already collapsed', {show: true});
                return;
            }

            console.log('Mark as read clicked but no container found', {show: true});
        }
    }

    document.addEventListener('click', function(e) {
        const toggleEl = e.target.closest('[data-issue-toggle]');
        if (!toggleEl) return;
        handleIssueToggle(toggleEl, e);
    });

    document.addEventListener('keydown', function(e) {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        const toggleEl = e.target.closest('[data-issue-toggle]');
        if (!toggleEl) return;
        if (toggleEl.tagName === 'BUTTON') return;
        handleIssueToggle(toggleEl, e);
    });
}

export function restoreReadState() {
    const readIssues = getReadIssues();
    const containers = document.querySelectorAll('.issue-header-container');

    containers.forEach(container => {
        const header = container.querySelector('h4');
        if (!header) return;

        const date = container.getAttribute('data-date');
        if (!date) return;

        const headerText = header.textContent.trim();
        const category = headerText.includes('AI') ? 'AI' : 'Tech';
        const issueKey = getIssueKey(date, category);

        if (isIssueRead(issueKey)) {
            markIssueAsRead(container);
        }
    });
}

// #endregion
