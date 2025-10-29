<script setup>
import { ref, computed, onMounted } from 'vue'
import { useScraper } from '@/composables/useScraper'

const emit = defineEmits(['results'])

const startDate = ref('')
const endDate = ref('')

const { scrape, loading, error, progress } = useScraper()

// Computed validation
const daysDiff = computed(() => {
  if (!startDate.value || !endDate.value) return 0
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  return Math.ceil((end - start) / (1000 * 60 * 60 * 24))
})

const validationError = computed(() => {
  if (!startDate.value || !endDate.value) return null

  const start = new Date(startDate.value)
  const end = new Date(endDate.value)

  if (start > end) {
    return 'Start date must be before or equal to end date.'
  }
  if (daysDiff.value >= 31) {
    return 'Date range cannot exceed 31 days. Please select a smaller range.'
  }
  return null
})

const isDisabled = computed(() => loading.value || !!validationError.value)

// Set default dates on mount
onMounted(() => {
  setDefaultDates()
})

function setDefaultDates() {
  const today = new Date()
  const threeDaysAgo = new Date(today)
  threeDaysAgo.setDate(today.getDate() - 3)

  endDate.value = today.toISOString().split('T')[0]
  startDate.value = threeDaysAgo.toISOString().split('T')[0]
}

async function handleSubmit() {
  if (validationError.value) return

  const results = await scrape(startDate.value, endDate.value)
  if (results) {
    emit('results', results)
  }
}
</script>

<template>
  <div>
    <form id="scrapeForm" @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="start_date">Start Date:</label>
        <input
          id="start_date"
          v-model="startDate"
          type="date"
          name="start_date"
          required
        >
      </div>

      <div class="form-group">
        <label for="end_date">End Date:</label>
        <input
          id="end_date"
          v-model="endDate"
          type="date"
          name="end_date"
          required
        >
      </div>

      <button
        id="scrapeBtn"
        type="submit"
        :disabled="isDisabled"
        data-testid="scrape-btn"
      >
        {{ loading ? 'Scraping...' : 'Scrape Newsletters' }}
      </button>
    </form>

    <!-- Progress bar -->
    <div v-if="loading" class="progress">
      <div id="progress-text">
        Scraping newsletters... This may take several minutes.
      </div>
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: `${progress}%` }"
        />
      </div>
    </div>

    <!-- Validation error -->
    <div v-if="validationError" class="error" role="alert">
      {{ validationError }}
    </div>

    <!-- Network error -->
    <div v-if="error" class="error" role="alert">
      Error: {{ error }}
    </div>
  </div>
</template>

<style scoped>
.form-group {
  margin-bottom: 20px;
  display: inline-block;
  width: 45%;
  margin-right: 5%;
}

.form-group:last-child {
  margin-right: 0;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
  color: var(--muted);
}

input[type="date"] {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 16px;
  box-sizing: border-box;
  background: var(--surface);
  color: var(--text);
  min-height: 44px;
}

button {
  background-color: #007bff;
  color: white;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  width: 100%;
  margin-top: 20px;
  min-height: 44px;
}

button:hover {
  background-color: #0056b3;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.progress {
  display: block;
  margin: 20px 0;
  padding: 15px;
  background-color: #e3f2fd;
  border-radius: 4px;
  border-left: 4px solid #2196f3;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background-color: #ddd;
  border-radius: 10px;
  overflow: hidden;
  margin-top: 10px;
}

.progress-fill {
  height: 100%;
  background-color: #2196f3;
  transition: width 0.3s ease;
}

.error {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  padding: 10px 12px;
  border-radius: 6px;
  margin-top: 10px;
}

@media (max-width: 480px) {
  .form-group {
    width: 100%;
    margin-right: 0;
  }
}
</style>
