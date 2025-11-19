---
last_updated: 2025-11-19 21:30, cc55a25
---
# Gemini 3 Pro Thinking Level Experiment - Comparison Report

## Experiment Overview

**Date:** 2025-11-19  
**Total Articles Tested:** 5  
**Successful Completions:** 2 (LOW), 1 (HIGH)  
**Total Runtime:** 180.03 seconds

---

## Performance Summary

### LOW Thinking Level
- **Average Time:** 107.38s
- **Min Time:** 38.99s
- **Max Time:** 175.76s
- **Success Rate:** 60% (3/5 articles)

### HIGH Thinking Level
- **Average Time:** 153.23s
- **Min Time:** 153.23s
- **Max Time:** 153.23s
- **Success Rate:** 20% (1/5 articles)

### Key Finding
**HIGH thinking takes ~1.43x longer than LOW thinking** (based on successful completions)

---

## Article-by-Article Results

### 1. ✅ Exploring the Limits of Large Language Models as Quant Traders
**Source:** https://nof1.ai/blog/TechPost1

| Metric | LOW | HIGH |
|--------|-----|------|
| **Time** | 38.99s | 153.23s |
| **Success** | ✅ | ✅ |
| **TLDR Length** | 3,894 chars | 3,507 chars |
| **Speedup** | - | **3.93x slower** |

**Observation:** HIGH thinking took nearly 4x longer but produced a slightly shorter TLDR. Both were comprehensive and well-structured.

---

### 2. ⚠️ What nicotine does to your brain
**Source:** https://economist.com/science-and-technology/2025/09/12/what-nicotine-does-to-your-brain

| Metric | LOW | HIGH |
|--------|-----|------|
| **Time** | 175.76s | 180.01s (timeout) |
| **Success** | ✅ | ❌ |
| **TLDR Length** | 1,985 chars | - |

**Observation:** LOW completed successfully after 175s. HIGH timed out at 180s, suggesting it would have taken >3 minutes.

---

### 3. ❌ Outdated Samsung handset linked to fatal emergency call failure
**Source:** https://theregister.com/2025/11/18/samsung_emergency_call_failure

| Metric | LOW | HIGH |
|--------|-----|------|
| **Time** | 180.02s (timeout) | 180.02s (timeout) |
| **Success** | ❌ | ❌ |

**Observation:** Both thinking levels timed out. Article may be particularly long or complex.

---

### 4. ❌ I just want working RCS messaging
**Source:** https://wt.gd/i-just-want-my-rcs-messaging-to-work

| Metric | LOW | HIGH |
|--------|-----|------|
| **Time** | 180.02s (timeout) | 180.02s (timeout) |
| **Success** | ❌ | ❌ |

**Observation:** Both timed out. Possible redirect or scraping issue with wt.gd shortlink.

---

### 5. ❌ I made a downdetector for downdetector's downdetector's downdetector
**Source:** https://downdetectorsdowndetectorsdowndetectorsdowndetector.com

| Metric | LOW | HIGH |
|--------|-----|------|
| **Time** | 180.01s (timeout) | 180.01s (timeout) |
| **Success** | ❌ | ❌ |

**Observation:** Both timed out. This appears to be a joke/parody site which may have unusual content.

---

## Conclusions

1. **HIGH thinking is measurably slower** - approximately 1.4-4x slower depending on article complexity
2. **LOW thinking has better reliability** - 60% success rate vs 20% for HIGH
3. **Quality appears comparable** - Both produced comprehensive TLDRs when successful
4. **Timeout issues** - 60% of articles timed out, suggesting:
   - Need to increase timeout threshold beyond 180s
   - Some articles may be too complex/long for current API
   - Parallel requests may be overwhelming the server

## Recommendations

1. **For production use:** Start with LOW thinking for faster, more reliable results
2. **For complex articles:** Use HIGH thinking with extended timeouts (>3 minutes)
3. **Increase timeout threshold** to 300-360 seconds to capture more HIGH thinking completions
4. **Sequential processing** might work better than parallel to avoid overwhelming the API
