---
name: state-machines/add-url
description: State machine for the toolbar's URL-to-article modal and auto-submit.
last_updated: 2026-05-23 12:56
---
# State Machines: Add URL

### 19. Add URL overlay

| | |
|---|---|
| **Pattern** | `useState` in `AddUrlOverlay`: `value`, `status`, `errorMessage` |
| **File** | `components/AddUrlButton.jsx` |
| **Scope** | Per-instance (mounted only while open) |

#### States

`status ∈ { idle, submitting, error }` combined with `value` surfaces as `data-state` on the overlay:

| `data-state` | When |
|---|---|
| `closed` | overlay not mounted |
| `empty` | open, value empty |
| `pending` | value non-empty, not a URL |
| `valid` | value passes `isLikelyUrl` (transient — auto-submit fires) |
| `submitting` | request in flight |
| `error` | request returned a failure |

#### Single Trigger Point

The input's `onChange` is the only entry point. There is no Enter handler — the user pastes, the input becomes valid, the request goes:

```js
if (status !== 'submitting' && isLikelyUrl(next.trim())) submitUrl(next.trim())
```

On error, editing the input clears `status` back to `idle` in the same handler, so the next valid keystroke immediately re-fires.

#### URL detection (`lib/urlDetection.js`)

Strip `https?://` and `www.`, split on `.`, require the first two parts to be non-empty AND the last label to be a known TLD (`lib/topLevelDomains.js` — bundled IANA list).

#### Closing

Backdrop click and `Escape` both call `onClose`, gated by `status !== 'submitting'`. On success, `submitUrl` itself calls `onClose` after `ingestDayPayload` + `emitToast`.

---
