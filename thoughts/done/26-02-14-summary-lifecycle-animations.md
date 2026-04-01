---
last_updated: 2026-04-01 18:05
description: Summary lifecycle animations: from complex touch phase state machine to simplified CSS-based spark-orbit.
---
# Summary Lifecycle Animations

## Problem
Summary loading lacked visual feedback, making the "magic" of AI generation feel invisible or broken during the 5-30s wait.

## Initial Solution (Feb 17, `c62aa7b`)
Implemented a complex, game-inspired "charge attack" animation lifecycle:
1.  **Axis 1 (Touch Phase)**: `idle` → `pressed` (ignition) → `released` (burst) via `useTouchPhase` hook and `touchPhaseReducer`.
2.  **Axis 2 (Data Status)**: Integrated with `summaryDataReducer` (`loading`, `available`, `error`).
3.  **Mechanism**: Card border "ignited" on touch, "charged" during hold, and "fired" a circuit-completion burst on release, transitioning into a traveling spark.

## Refinement / Simplification (Feb 20, `387f06f`)
The `useTouchPhase` implementation was removed because it conflicted with the global selection mode and long-press gestures (Selectable).

**Current Implementation**:
- **Simplified Visuals**: A single luminous "spark" orbits the card border while loading (`spark-orbit` keyframes) + subtle digital distortion on text (`text-distort`).
- **Trigger**: CSS targeting `[data-summary-status="loading"]::after`.
- **Shared Constants**: Moved `LONG_PRESS_THRESHOLD_MS` and `POINTER_MOVE_THRESHOLD_PX` to `client/src/lib/interactionConstants.js` for cross-hook consistency.

## Key Primitives
- `data-summary-status`: DOM attribute for CSS targeting.
- `@property --border-angle`: GPU-composited angle for smooth conic-gradient animation.
- `interactionConstants.js`: Single source of truth for gesture thresholds.
