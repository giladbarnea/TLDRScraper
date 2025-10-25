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

export function bindIssueToggleControls() {
    function handleIssueToggle(element, event) {
        event.preventDefault();
        event.stopPropagation();

        const issueKey = element.getAttribute('data-issue-toggle');
        const issueContainer = findIssueContainer(issueKey, element);

        if (!issueContainer) return;
        toggleIssueContent(issueContainer);
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
