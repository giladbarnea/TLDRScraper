/**
 * Quake-style console overlay for mobile debugging.
 * Intercepts console.log/warn/error and displays them in a draggable overlay.
 */

let overlay = null
let toggleButton = null
let isVisible = false
let isUserScrolledUp = false

const STYLES = {
  overlay: {
    position: 'fixed',
    bottom: '0',
    left: '0',
    width: '100%',
    height: '40vh',
    overflowY: 'scroll',
    pointerEvents: 'auto',
    zIndex: '9999',
    padding: '10px',
    paddingBottom: '50px',
    boxSizing: 'border-box',
    fontFamily: 'monospace',
    fontSize: '12px',
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    color: '#0f0',
    textShadow: '0 0 2px #0f0',
    backdropFilter: 'blur(2px)',
    webkitOverflowScrolling: 'touch',
    display: 'none',
    borderTop: '2px solid #0f0'
  },
  toggleButton: {
    position: 'fixed',
    bottom: '10px',
    right: '10px',
    width: '44px',
    height: '44px',
    borderRadius: '50%',
    backgroundColor: 'rgba(0, 255, 0, 0.2)',
    border: '2px solid #0f0',
    color: '#0f0',
    fontSize: '20px',
    fontFamily: 'monospace',
    zIndex: '10000',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 0 10px rgba(0, 255, 0, 0.3)'
  },
  logLine: {
    marginBottom: '4px',
    borderBottom: '1px solid rgba(0, 255, 0, 0.2)',
    paddingBottom: '4px',
    wordBreak: 'break-word'
  },
  colors: {
    log: '#0f0',
    warn: '#ff0',
    error: '#f44',
    info: '#0ff'
  }
}

function formatArgs(args) {
  return args.map(arg => {
    if (arg instanceof Error) return `${arg.name}: ${arg.message}`
    if (typeof arg === 'object') {
      try {
        return JSON.stringify(arg, null, 2)
      } catch {
        return String(arg)
      }
    }
    return String(arg)
  }).join(' ')
}

function formatTimestamp() {
  const now = new Date()
  return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}`
}

function addLog(type, args) {
  if (!overlay) return

  const line = document.createElement('div')
  const timestamp = formatTimestamp()
  const prefix = type === 'error' ? '✖' : type === 'warn' ? '⚠' : '›'
  line.textContent = `${timestamp} ${prefix} ${formatArgs(args)}`

  Object.assign(line.style, STYLES.logLine)
  line.style.color = STYLES.colors[type] || STYLES.colors.log

  overlay.appendChild(line)

  if (!isUserScrolledUp) {
    overlay.scrollTop = overlay.scrollHeight
  }
}

function toggle() {
  isVisible = !isVisible
  overlay.style.display = isVisible ? 'block' : 'none'
  toggleButton.textContent = isVisible ? '×' : '~'
  toggleButton.style.backgroundColor = isVisible
    ? 'rgba(255, 0, 0, 0.2)'
    : 'rgba(0, 255, 0, 0.2)'
  toggleButton.style.borderColor = isVisible ? '#f44' : '#0f0'
  toggleButton.style.color = isVisible ? '#f44' : '#0f0'
}

function createOverlay() {
  overlay = document.createElement('div')
  overlay.id = 'quake-console'
  Object.assign(overlay.style, STYLES.overlay)

  overlay.addEventListener('scroll', () => {
    const distanceFromBottom = overlay.scrollHeight - overlay.scrollTop - overlay.clientHeight
    isUserScrolledUp = distanceFromBottom > 20
  })

  document.body.appendChild(overlay)
}

function createToggleButton() {
  toggleButton = document.createElement('button')
  toggleButton.id = 'quake-console-toggle'
  toggleButton.textContent = '~'
  Object.assign(toggleButton.style, STYLES.toggleButton)
  toggleButton.addEventListener('click', toggle)
  document.body.appendChild(toggleButton)
}

function interceptConsole() {
  ['log', 'warn', 'error', 'info'].forEach(method => {
    const original = console[method]
    console[method] = (...args) => {
      original.apply(console, args)
      addLog(method, args)
    }
  })
}

export function initQuakeConsole() {
  if (overlay) return

  createOverlay()
  createToggleButton()
  interceptConsole()

  console.log('Quake console initialized')
}
