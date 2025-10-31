<script setup>
import { computed, ref, watchEffect, onMounted, onUnmounted } from 'vue'
import ArticleCard from './ArticleCard.vue'

const props = defineProps({
  articles: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['copy-summary'])

// Force re-computation trigger for storage changes
const storageVersion = ref(0)

// Watch for localStorage changes
function handleStorageChange() {
  storageVersion.value++
}

onMounted(() => {
  // Listen for storage changes (from useLocalStorage's deep watcher)
  window.addEventListener('local-storage-change', handleStorageChange)
})

onUnmounted(() => {
  window.removeEventListener('local-storage-change', handleStorageChange)
})

// Get live article state from localStorage for sorting
function getArticleState(article) {
  // Access storageVersion to make this reactive to storage changes
  storageVersion.value

  const storageKey = `newsletters:scrapes:${article.issueDate}`
  try {
    const raw = localStorage.getItem(storageKey)
    if (raw) {
      const payload = JSON.parse(raw)
      const liveArticle = payload.articles?.find(a => a.url === article.url)
      if (liveArticle) {
        // Use live state from localStorage
        if (liveArticle.removed) return 3  // Removed articles last
        if (liveArticle.tldrHidden) return 2  // TLDR hidden articles second to last
        if (liveArticle.read?.isRead) return 1  // Read articles middle
        return 0  // Unread articles first
      }
    }
  } catch (err) {
    console.error('Failed to read from localStorage:', err)
  }

  // Fallback to prop values if storage not available
  if (article.removed) return 3
  if (article.tldrHidden) return 2
  if (article.read?.isRead) return 1
  return 0
}

// Sort articles by state, then by original order
const sortedArticles = computed(() => {
  return [...props.articles].sort((a, b) => {
    const stateDiff = getArticleState(a) - getArticleState(b)
    if (stateDiff !== 0) return stateDiff

    // Within same state, preserve original order
    const orderA = a.originalOrder ?? 0
    const orderB = b.originalOrder ?? 0
    return orderA - orderB
  })
})

// Build sections with their articles
const sectionsWithArticles = computed(() => {
  const sections = []
  let currentSection = null

  sortedArticles.value.forEach((article, index) => {
    const sectionTitle = article.section
    const sectionEmoji = article.sectionEmoji
    const sectionKey = sectionTitle ? `${sectionEmoji || ''} ${sectionTitle}`.trim() : null

    // Check if we need a new section
    if (sectionKey && sectionKey !== currentSection) {
      sections.push({
        type: 'section',
        key: sectionKey,
        label: sectionKey
      })
      currentSection = sectionKey
    } else if (!sectionTitle && currentSection !== null) {
      // Reset section when we encounter an article without one
      currentSection = null
    }

    // Add the article
    sections.push({
      type: 'article',
      key: article.url,
      article: article,
      index: index
    })
  })

  return sections
})

// Track which sections have state changes for boundary markers
const articlesWithBoundaries = computed(() => {
  let lastState = -1
  return sortedArticles.value.map(article => {
    const currentState = getArticleState(article)
    const isFirstInCategory = currentState !== lastState && lastState !== -1
    lastState = currentState

    return {
      ...article,
      isFirstInCategory
    }
  })
})

function handleCopySummary() {
  emit('copy-summary')
}
</script>

<template>
  <div class="article-list">
    <template v-for="item in sectionsWithArticles" :key="item.key">
      <!-- Section title -->
      <div v-if="item.type === 'section'" class="section-title">
        {{ item.label }}
      </div>

      <!-- Article card -->
      <ArticleCard
        v-else
        :article="item.article"
        :index="item.index"
        :class="{ 'category-first': item.article.isFirstInCategory }"
        @copy-summary="handleCopySummary"
      />
    </template>
  </div>
</template>

<style scoped>
.article-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 20px 0;
  padding: 0;
  list-style: none;
}

.section-title {
  margin: 18px 0 6px;
  text-align: center;
  font-style: italic;
  color: #9ca3af;
  font-size: 0.92em;
  letter-spacing: 0.01em;
}

/* Category boundaries - first item in a new category */
:deep(.article-card.category-first) {
  border-top: 3px solid var(--link, #1a73e8);
  padding-top: 16px;
  margin-top: 12px;
}
</style>
