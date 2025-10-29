<script setup>
import { computed } from 'vue'
import { useArticleState } from '@/composables/useArticleState'
import { useSummary } from '@/composables/useSummary'

const props = defineProps({
  article: {
    type: Object,
    required: true
  },
  index: {
    type: Number,
    required: true
  }
})

const emit = defineEmits(['copy-summary'])

// Destructure article state management
const { isRead, isRemoved, toggleRead, toggleRemove } = useArticleState(
  props.article.issueDate,
  props.article.url
)

// Setup summary and tldr composables
const summary = useSummary(props.article.issueDate, props.article.url, 'summary')
const tldr = useSummary(props.article.issueDate, props.article.url, 'tldr')

// Computed classes for card styling
const cardClasses = computed(() => ({
  'article-card': true,
  'unread': !isRead.value,
  'read': isRead.value,
  'removed': isRemoved.value
}))

// Favicon URL
const faviconUrl = computed(() => {
  try {
    const url = new URL(props.article.url)
    return `${url.origin}/favicon.ico`
  } catch {
    return null
  }
})

// Handle link click - expand summary instead of navigating
function handleLinkClick(e) {
  if (isRemoved.value) return
  if (e.ctrlKey || e.metaKey) return  // Allow cmd/ctrl+click for new tab
  e.preventDefault()
  summary.toggle()
  if (!isRead.value) {
    toggleRead()
  }
}

// Copy summary to clipboard
async function copyToClipboard() {
  const text = `---
title: ${props.article.title}
url: ${props.article.url}
---
${summary.markdown.value}`

  try {
    await navigator.clipboard.writeText(text)
    emit('copy-summary')
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

// Handle TLDR click
function handleTldrClick() {
  if (isRemoved.value) return
  tldr.toggle()
  if (!isRead.value && tldr.expanded.value) {
    toggleRead()
  }
}
</script>

<template>
  <div :class="cardClasses" :data-original-order="index">
    <div class="article-header">
      <!-- Article number -->
      <div class="article-number">{{ index + 1 }}</div>

      <!-- Article link -->
      <div class="article-content">
        <a
          :href="article.url"
          class="article-link"
          target="_blank"
          rel="noopener noreferrer"
          :data-url="article.url"
          :tabindex="isRemoved ? -1 : 0"
          @click="handleLinkClick"
        >
          <img
            v-if="faviconUrl"
            :src="faviconUrl"
            class="article-favicon"
            loading="lazy"
            alt=""
            @error="$event.target.style.display='none'"
          >
          <span class="article-link-text">{{ article.title }}</span>
        </a>
      </div>

      <!-- Article actions -->
      <div class="article-actions">
        <!-- Summary button with effort dropdown -->
        <div class="expand-btn-container">
          <button
            class="article-btn expand-btn"
            :class="{
              loaded: summary.isAvailable.value,
              expanded: summary.expanded.value
            }"
            :disabled="summary.loading.value"
            type="button"
            :title="summary.isAvailable.value ? 'Summary cached - click to show' : 'Show summary with default reasoning effort'"
            @click="summary.toggle()"
          >
            {{ summary.buttonLabel.value }}
          </button>

          <!-- TODO: Add effort dropdown in next iteration -->
          <button
            class="article-btn expand-chevron-btn"
            type="button"
            title="Choose reasoning effort level"
          >
            ▾
          </button>
        </div>

        <!-- TLDR button -->
        <button
          class="article-btn tldr-btn"
          :class="{
            loaded: tldr.isAvailable.value,
            expanded: tldr.expanded.value
          }"
          :disabled="tldr.loading.value"
          type="button"
          :title="tldr.isAvailable.value ? 'TLDR cached - click to show' : 'Show TLDR'"
          @click="handleTldrClick"
        >
          {{ tldr.buttonLabel.value }}
        </button>

        <!-- Copy summary button -->
        <button
          v-if="summary.isAvailable.value"
          class="article-btn copy-summary-btn visible"
          type="button"
          title="Copy summary"
          @click="copyToClipboard"
        >
          <svg
            aria-hidden="true"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>

        <!-- Remove/Restore button -->
        <button
          class="article-btn remove-article-btn"
          type="button"
          :title="isRemoved ? 'Restore this article to the list' : 'Remove this article from the list'"
          @click="toggleRemove"
        >
          {{ isRemoved ? 'Restore' : 'Remove' }}
        </button>
      </div>
    </div>

    <!-- Inline summary expansion -->
    <div v-if="summary.expanded.value && summary.html.value" class="inline-summary">
      <strong>Summary</strong>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-html="summary.html.value" />
    </div>

    <!-- Inline TLDR expansion -->
    <div v-if="tldr.expanded.value && tldr.html.value" class="inline-tldr">
      <strong>TLDR</strong>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-html="tldr.html.value" />
    </div>
  </div>
</template>

<style scoped>
/* Article card base styles */
.article-card {
  display: flex;
  flex-direction: column;
  background: var(--surface, #ffffff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  padding: 14px 16px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease, opacity 0.15s ease;
  position: relative;
  animation: cardFadeIn 0.3s ease backwards;
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.article-card:hover {
  border-color: var(--link, #1a73e8);
  box-shadow: 0 2px 8px rgba(26, 115, 232, 0.12);
  transform: translateY(-1px);
}

/* Article state styling */
.article-card.unread .article-link {
  font-weight: 600;
}

.article-card.read .article-link {
  font-weight: normal;
  color: var(--muted, #475569);
}

.article-card.removed {
  opacity: 0.75;
  border-style: dashed;
  background: rgba(220, 53, 69, 0.06);
}

.article-card.removed .article-link {
  text-decoration: line-through;
  color: var(--muted, #475569);
  pointer-events: none;
}

.article-card.removed .article-actions {
  opacity: 1;
}

.article-card.removed .article-actions .article-btn:not(.remove-article-btn) {
  display: none;
}

/* Article header layout */
.article-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.article-number {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg, #f6f7f9);
  border-radius: 6px;
  font-weight: 600;
  font-size: 14px;
  color: var(--muted, #475569);
}

.article-content {
  flex: 1;
  min-width: 0;
}

.article-link {
  font-size: 16px;
  line-height: 1.5;
  color: var(--link, #1a73e8);
  text-decoration: none;
  word-wrap: break-word;
  display: block;
  width: 100%;
  cursor: pointer;
}

.article-link:hover {
  text-decoration: underline;
}

.article-favicon {
  width: 1em;
  height: 1em;
  display: inline-block;
  vertical-align: -0.125em;
  object-fit: contain;
  margin-right: 1ch;
}

/* Article actions */
.article-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.article-card:hover .article-actions {
  opacity: 1;
}

/* Base button styles */
.article-btn {
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 6px;
  color: var(--muted, #475569);
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 13px;
  padding: 0;
  margin: 0;
}

.article-btn:hover {
  background: var(--bg, #f6f7f9);
  border-color: var(--muted, #475569);
  color: var(--text, #0f172a);
}

.article-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Split button container */
.expand-btn-container {
  position: relative;
  display: flex;
  align-items: center;
  height: 32px;
}

.expand-btn {
  width: auto;
  min-width: 7em;
  padding: 0 10px;
  font-weight: 500;
  white-space: nowrap;
  border-radius: 6px 0 0 6px;
  border-right: none;
}

.expand-chevron-btn {
  width: 38px;
  border-radius: 0 6px 6px 0;
}

.expand-btn.loaded {
  background: #22c55e;
  color: white;
  border-color: #22c55e;
}

.expand-btn.loaded:hover {
  background: #16a34a;
  border-color: #16a34a;
}

.expand-btn.loaded.expanded {
  background: transparent;
  color: var(--text, #0f172a);
  border-color: var(--border, #e5e7eb);
}

/* TLDR button */
.tldr-btn {
  width: auto;
  min-width: 5em;
  padding: 0 10px;
  font-weight: 500;
  white-space: nowrap;
}

.tldr-btn.loaded {
  background: #22c55e;
  color: white;
  border-color: #22c55e;
}

.tldr-btn.loaded:hover {
  background: #16a34a;
  border-color: #16a34a;
}

.tldr-btn.loaded.expanded {
  background: var(--bg, #f6f7f9);
  color: var(--text, #0f172a);
  border-color: var(--border, #e5e7eb);
}

/* Copy button */
.copy-summary-btn {
  width: 32px;
  display: none;
  font-size: 16px;
}

.copy-summary-btn.visible {
  display: inline-flex;
  background: #f3f4f6;
  border-color: rgba(15, 23, 42, 0.08);
  color: #1f2937;
}

.copy-summary-btn.visible:hover {
  background: #e5e7eb;
  border-color: rgba(15, 23, 42, 0.12);
  color: #111827;
}

/* Remove button */
.remove-article-btn {
  width: auto;
  min-width: 6.2em;
  padding: 0 10px;
  font-weight: 500;
  white-space: nowrap;
}

.remove-article-btn:hover {
  background: rgba(220, 53, 69, 0.12);
  border-color: rgba(220, 53, 69, 0.4);
  color: #b91c1c;
}

.article-card.removed .remove-article-btn {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(5, 150, 105, 0.45);
  color: #047857;
}

.article-card.removed .remove-article-btn:hover {
  background: rgba(22, 163, 74, 0.16);
  border-color: rgba(21, 128, 61, 0.6);
  color: #065f46;
}

/* Inline summary/tldr expansion */
.inline-summary,
.inline-tldr {
  margin-top: 9px;
  padding-top: 9px;
  padding-left: 16px;
  padding-right: 16px;
  padding-bottom: 0;
  border-top: 1px dashed var(--border, #e5e7eb);
  font-size: 0.96em;
  line-height: 1.675;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.inline-summary strong,
.inline-tldr strong {
  display: block;
  margin-bottom: 0.5em;
  color: var(--text, #0f172a);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .article-actions {
    opacity: 1;
    width: 100%;
    margin-left: 0;
    margin-top: 8px;
    justify-content: flex-start;
  }

  .article-header {
    flex-wrap: wrap;
  }

  .article-btn.expand-btn {
    font-size: 12px;
    padding: 0 8px;
  }
}
</style>
