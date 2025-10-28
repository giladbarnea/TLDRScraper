# Fix Cache-UI State Sync Implementation Plan

## Overview

Fix state sync issues where UI updates happen without re-syncing with localStorage, causing potential cache/UI drift across TLDR, Summary, Remove, and Read features.

## Current State Analysis

All state mutations follow a flawed pattern:
1. Update UI directly
2. Save to localStorage via `updateStoredArticleFromCard()`
3. Never call `applyStoredArticleState()` to re-sync

`applyStoredArticleState()` exists but only runs on initial render - never after mutations.

### Key Discoveries:
- `applyStoredArticleState()` in `dom-builder.js:583-735` properly syncs cache to UI
- Called only in: `app.js:28`, `scrape.js:66`, `scrape.js:100` (initial renders only)
- All mutations update UI-first, storage-second (wrong order)
- `markArticleAsRead()` exists but no `markArticleAsUnread()` (asymmetrical)

## Desired End State

As a user:
- When I generate TLDR/Summary, refresh shows correct "Available" state
- When I remove/restore article, state persists correctly even if partial failure
- All state changes are atomic: storage first, UI second
- Read/unread state can toggle both directions

Technically:
- Storage updates before UI changes
- All mutations trigger `reapplyArticleState()` re-sync
- Consistent state between cache and UI at all times

## What We're NOT Doing

- Not refactoring the entire state management system
- Not changing the localStorage schema
- Not adding optimistic UI updates
- Not building an undo/redo system

## Implementation Approach

Create minimal re-sync helper, reverse update order (storage-first), add re-sync calls after mutations.

## Phase 1: Infrastructure

### Overview
Create `reapplyArticleState()` helper to re-sync single article from localStorage.

### Changes Required:

#### 1. Storage Module
**File**: `storage.js`
**Changes**: Export helper to read single article from cache by URL and date

#### 2. DOM Builder Module
**File**: `dom-builder.js`
**Changes**: Create `reapplyArticleState(date, url)` that reads from storage and calls `applyStoredArticleState()` for one article

## Phase 2: Fix Mutation Order

### Overview
Reverse order: storage update FIRST, UI update SECOND.

### Changes Required:

#### 1. Remove/Restore Handler
**File**: `ui-utils.js:44-62`
**Changes**: Call `updateStoredArticleFromCard()` before `setCardRemovedState()`

#### 2. Read State Handler
**File**: `article-card.js:200-212`
**Changes**: Call `updateStoredArticleFromCard()` before UI class changes

## Phase 3: Add Re-sync Calls

### Overview
Call `reapplyArticleState()` after every mutation.

### Changes Required:

#### 1. TLDR Handler
**File**: `tldr.js:72-80, 131-140`
**Changes**: Call `reapplyArticleState()` after storage update

#### 2. Summary Handler
**File**: `summary.js:193-202, 258-267`
**Changes**: Call `reapplyArticleState()` after storage update

#### 3. Remove Handler
**File**: `ui-utils.js:57-60`
**Changes**: Call `reapplyArticleState()` after storage update

#### 4. Read Handler
**File**: `article-card.js:205-211`
**Changes**: Call `reapplyArticleState()` after storage update

## Phase 4: Add Missing Features

### Overview
Implement `markArticleAsUnread()` for symmetry.

### Changes Required:

#### 1. Article Card Module
**File**: `article-card.js`
**Changes**: Add `markArticleAsUnread()` function (mirror of `markArticleAsRead()`)
