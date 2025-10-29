<script setup>
import { computed, ref } from 'vue'
import ArticleList from './ArticleList.vue'

const props = defineProps({
  results: {
    type: Object,
    required: true
  }
})

const showToast = ref(false)
let toastTimeout = null

// Build stats display
const statsLines = computed(() => {
  const stats = props.results.stats
  const lines = [
    `📊 Stats: ${stats.total_articles} articles, ${stats.unique_urls} unique URLs`,
    `📅 Dates: ${stats.dates_with_content}/${stats.dates_processed} with content`
  ]

  if (props.results.source) {
    lines.push(`Source: ${props.results.source}`)
  }

  return lines
})

// Group articles by date
const articlesByDate = computed(() => {
  const payloads = props.results.payloads || []
  return payloads.map(payload => ({
    date: payload.date,
    articles: payload.articles.map((article, index) => ({
      ...article,
      originalOrder: index
    })),
    issues: payload.issues || []
  }))
})

// Debug logs (if any)
const debugLogs = computed(() => props.results.debugLogs || [])

function handleCopySummary() {
  clearTimeout(toastTimeout)
  showToast.value = true
  toastTimeout = setTimeout(() => {
    showToast.value = false
  }, 2000)
}
</script>

<template>
  <div id="result" class="result success">
    <!-- Stats display -->
    <div class="stats">
      <div v-for="(line, index) in statsLines" :key="index">
        {{ line }}
      </div>
    </div>

    <!-- Debug logs (collapsible) -->
    <div v-if="debugLogs.length > 0" id="logs-slot" class="logs-slot">
      <details>
        <summary>Debug logs</summary>
        <pre>{{ debugLogs.join('\n') }}</pre>
      </details>
    </div>

    <!-- Articles grouped by date -->
    <main id="write">
      <div
        v-for="dateGroup in articlesByDate"
        :key="dateGroup.date"
        class="date-group"
      >
        <!-- Date header -->
        <div class="date-header-container" :data-date="dateGroup.date">
          <h2>{{ dateGroup.date }}</h2>
        </div>

        <!-- Issues/Categories -->
        <div
          v-for="issue in dateGroup.issues"
          :key="`${dateGroup.date}-${issue.category}`"
          class="issue-section"
        >
          <div class="issue-header-container">
            <h4>{{ issue.category }}</h4>
          </div>

          <!-- Issue title block (if present) -->
          <div v-if="issue.title || issue.subtitle" class="issue-title-block">
            <div v-if="issue.title" class="issue-title-line">
              {{ issue.title }}
            </div>
            <div v-if="issue.subtitle && issue.subtitle !== issue.title" class="issue-title-line">
              {{ issue.subtitle }}
            </div>
          </div>

          <!-- Articles for this issue/category -->
          <ArticleList
            :articles="dateGroup.articles.filter(a => a.category === issue.category)"
            @copy-summary="handleCopySummary"
          />
        </div>

        <!-- Articles without a category -->
        <ArticleList
          v-if="dateGroup.articles.some(a => !a.category)"
          :articles="dateGroup.articles.filter(a => !a.category)"
          @copy-summary="handleCopySummary"
        />
      </div>
    </main>

    <!-- Copy toast notification -->
    <Teleport to="body">
      <div
        id="copyToast"
        :class="{ show: showToast }"
        class="copy-toast"
      >
        Copied to clipboard
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.result {
  margin-top: 20px;
  padding: 0;
  background-color: transparent;
  border-radius: 0;
  display: block;
  border: none;
}

.stats {
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 4px;
}

.logs-slot {
  margin-bottom: 15px;
}

.logs-slot details {
  background: #f6f7f9;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.logs-slot summary {
  cursor: pointer;
  font-weight: 600;
  color: #475569;
  user-select: none;
}

.logs-slot pre {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #0f172a;
}

/* Date headers */
.date-header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin: 0;
}

.date-header-container h2 {
  text-align: center;
  width: 100%;
  font-weight: normal;
  color: var(--text, #0f172a);
  margin-top: 2em;
}

.date-header-container h2::after {
  border-bottom: 1px solid #2f2f2f;
  content: '';
  width: 100px;
  display: block;
  margin: 0.4em auto 0;
  height: 1px;
}

/* Issue headers */
.issue-header-container h4 {
  text-align: left;
  margin: 1.5em 0 0.5em;
  font-style: normal;
  color: var(--text, #0f172a);
}

.issue-title-block {
  margin: 12px 0 18px;
  text-align: center;
  font-style: italic;
  color: #9ca3af;
  font-size: 0.95em;
  line-height: 1.6;
}

.issue-title-block .issue-title-line + .issue-title-line {
  margin-top: 4px;
}

/* Copy toast */
.copy-toast {
  position: fixed;
  left: 50%;
  bottom: 32px;
  transform: translateX(-50%) translateY(20px);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  color: var(--text, #0f172a);
  padding: 10px 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 500;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s ease, transform 0.25s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.06);
  z-index: 999;
}

.copy-toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}
</style>
