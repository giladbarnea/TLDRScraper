---
name: state-machines/add-url
description: State machine for the toolbar's URL-to-article modal and auto-submit.
last_updated: 2026-05-24 05:46, be365c0
---
# State Machines: Add URL

### 19. Add URL overlay

| | |
|---|---|
| **Pattern** | `useState` in `AddUrlOverlay`: `value`, `status`, `errorMessage` |
| **File** | `components/AddUrlButton.jsx` |
| **Scope** | Per-instance (mounted only while open) |

#### States

The component holds a request `status ∈ { idle, submitting, error }` and the input `value`. The two combine into the overlay's `data-state` attribute:

| `data-state` | `status` × `value` |
|---|---|
| `submitting` | request in flight |
| `error` | request returned a failure |
| `empty` | idle, value empty |
| `pending` | idle, value non-empty but not a URL |
| `valid` | idle, value passes `isLikelyUrl` (transient — auto-submit fires) |

#### Single trigger point

The input's `onChange` is the only entry point. There is no Enter handler — the user pastes, the input becomes valid, the request goes:

```js
if (!isSubmitting && isLikelyUrl(next.trim())) submitUrl(next.trim())
```

On error, editing the input flips `status` back to `idle` in the same handler, so the next valid keystroke immediately re-fires.

#### URL detection (`lib/urlDetection.js`)

Strip `https?://` and `www.`, split on `.`, require the first two parts to be non-empty AND the last label to be a known TLD (`lib/topLevelDomains.js` — bundled IANA list).

#### Closing

Backdrop click and `Escape` both call `onClose`, gated by `!isSubmitting`. On success, `submitUrl` itself calls `onClose` after `ingestDayPayload` + `emitToast`.

---
