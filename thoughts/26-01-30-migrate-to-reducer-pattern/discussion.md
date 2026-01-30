# Discussion: Cross-domain (cross state-machine) Reducer pattern state management

The most obvious next place is the ArticleCard “interaction stack” (the card + TLDR expansion + Zen overlay + swipe-to-remove + read/removed transitions + error toast).

Right now that behavior is distributed across:
	•	ArticleCard.jsx local logic (handleCardClick, conditional rendering of ZenModeOverlay, swipe enabling)
	•	useSummary (TLDR states: loading/available/error/expanded/html)
	•	useSwipeToRemove (drag state machine)
	•	usePullToClose and useOverscrollUp inside ZenModeOverlay
	•	useArticleState (removed/read state) plus async persistence

That’s exactly the pattern that tends to become “it works, but nobody can reason about it end-to-end”.

## Why a reducer helps here

A reducer gives you:
	•	one canonical state representation for the card’s UI mode
	•	explicit event transitions (tap, long press, swipe start, swipe commit, open overlay, close overlay, mark done)
	•	a single place to enforce invariants like:
	    •	“tap toggles TLDR only when not in select mode”
	    •	“if the last child ArticleCard of a container (like Newsletter)'s `removed` becomes true, remove & collapse its container”
	    •	“error toast lifecycle does not fight other transitions”

### What I would model (roughly - I'm not in the details)

A reducer per card (or shared reducer with articleId).
Domains that need to be covered: 
- ZenOverlay
- swipe: { status: 'idle' | 'dragging' | 'settling', dx: number }
- persistence (removed, ?)
- tldr: { status: 'idle' | 'loading' | 'ready' | 'read', 'error', html?: string, error?: string }
- toast: { message: string | null }
- any other domain I might have missed.

Events (examples - some are irrelevant, others are misplaced, some are missing. Do the research yourself)
	•	CARD_TAP
	•	TLDR_REQUESTED / TLDR_SUCCEEDED / TLDR_FAILED
	•	ZEN_OPEN / ZEN_CLOSE
	•	SWIPE_START / SWIPE_MOVE / SWIPE_CANCEL / SWIPE_COMMIT
	•	MARK_DONE
	•	REMOVED_TOGGLE_REQUESTED / REMOVED_TOGGLE_SUCCEEDED / REMOVED_TOGGLE_FAILED
	•	SHOW_ERROR / DISMISS_ERROR

Then hooks like useSwipeToRemove, usePullToClose, useOverscrollUp become either:
	•	“event sources” (they dispatch events), or
	•	internal reducer logic with some small imperative glue.
