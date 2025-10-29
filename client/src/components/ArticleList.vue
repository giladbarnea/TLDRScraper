<script setup>
import { computed } from 'vue'
import ArticleCard from './ArticleCard.vue'

const props = defineProps({
  articles: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['copy-summary'])

// Get article state for sorting
function getArticleState(article) {
  if (article.removed) return 2  // Removed articles last
  if (article.read?.isRead) return 1  // Read articles middle
  return 0  // Unread articles first
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
