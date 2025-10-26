/**
 * Client-side logging API for user-visible logs.
 * Logs are collected and displayed in the debug logs slot at the top of results.
 */

const CLIENT_LOGS = [];
const MAX_LOGS = 100;

/**
 * Add a client-side log message that will be visible to the user.
 * @param {string} message - The log message
 * @param {Object} options - Options for the log
 * @param {boolean} options.error - Whether this is an error log (default: false)
 */
export function clientLog(message, options = {}) {
    const isError = options.error || false;
    const timestamp = new Date().toISOString();

    const logEntry = {
        message: String(message),
        isError,
        timestamp,
        source: 'client'
    };

    CLIENT_LOGS.push(logEntry);

    // Keep only last MAX_LOGS entries
    if (CLIENT_LOGS.length > MAX_LOGS) {
        CLIENT_LOGS.shift();
    }

    // Still log to console for developers
    if (isError) {
        console.error(message);
    } else {
        console.log(message);
    }

    // Try to add to existing logs-slot if it exists
    updateLogsSlotIfExists();
}

/**
 * Get all client logs for rendering.
 * @returns {Array} Copy of client logs array
 */
export function getClientLogs() {
    return CLIENT_LOGS.slice();
}

/**
 * Clear all client logs.
 */
export function clearClientLogs() {
    CLIENT_LOGS.length = 0;
}

/**
 * Format client logs for display.
 * @returns {string[]} Array of formatted log strings
 */
export function formatClientLogs() {
    return CLIENT_LOGS.map(log => {
        const level = log.isError ? 'ERROR' : 'INFO';
        const time = new Date(log.timestamp).toLocaleTimeString();
        return `[Client] ${time} ${level}: ${log.message}`;
    });
}

/**
 * Update the logs slot dynamically if it exists.
 * This allows new client logs to appear even after initial render.
 */
function updateLogsSlotIfExists() {
    const slot = document.getElementById('logs-slot');
    if (!slot) return;

    // Find existing details element
    let details = slot.querySelector('details');
    if (!details) return;

    // Find the pre element with logs
    let pre = details.querySelector('pre');
    if (!pre) return;

    // Get existing content (server logs)
    const existingLogs = pre.textContent;

    // Append client logs if we have any
    if (CLIENT_LOGS.length > 0) {
        const clientLogLines = formatClientLogs();
        const separator = existingLogs && !existingLogs.endsWith('\n') ? '\n' : '';
        pre.textContent = existingLogs + separator + clientLogLines.join('\n');
    }
}
