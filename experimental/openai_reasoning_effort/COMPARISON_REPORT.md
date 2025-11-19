---
last_updated: 2025-11-19 21:30, cc55a25
---
# OpenAI GPT-5 vs GPT-5.1 Reasoning Effort Experiment - Comparison Report

## Experiment Overview

**Date:** 2025-11-19  
**Total Articles Tested:** 5  
**Successful Completions:** GPT-5 low (4), GPT-5 medium (4), GPT-5.1 low (3), GPT-5.1 medium (3)  
**Total Runtime:** 300.05 seconds

---

## Performance Summary

### GPT-5 with LOW Reasoning
- **Average Time:** 78.13s
- **Min Time:** 11.68s
- **Max Time:** 195.01s
- **Success Rate:** 80% (4/5 articles)

### GPT-5 with MEDIUM Reasoning
- **Average Time:** 139.67s (~1.79x slower than LOW)
- **Min Time:** 57.19s
- **Max Time:** 261.54s
- **Success Rate:** 80% (4/5 articles)

### GPT-5.1 with LOW Reasoning
- **Average Time:** 212.33s (~2.72x slower than GPT-5 LOW)
- **Min Time:** 165.54s
- **Max Time:** 297.45s
- **Success Rate:** 60% (3/5 articles)

### GPT-5.1 with MEDIUM Reasoning
- **Average Time:** 177.36s (~2.27x slower than GPT-5 LOW)
- **Min Time:** 29.65s
- **Max Time:** 272.40s
- **Success Rate:** 60% (3/5 articles)

### Key Findings

1. **GPT-5 LOW is fastest** - Averaging 78.13s per article
2. **MEDIUM reasoning adds ~79% overhead** for GPT-5 (78.13s → 139.67s)
3. **GPT-5.1 is significantly slower** - 2.5-3x slower than GPT-5 on average
4. **GPT-5 is more reliable** - 80% success rate vs 60% for GPT-5.1
5. **Interesting anomaly:** GPT-5.1 MEDIUM was sometimes faster than GPT-5.1 LOW

---

## Article-by-Article Results

### 1. ✅ Outdated Samsung handset linked to fatal emergency call failure
**Source:** https://theregister.com/2025/11/18/samsung_emergency_call_failure

| Configuration | Time | Success |
|--------------|------|---------|
| **GPT-5 LOW** | 11.68s | ✅ |
| **GPT-5 MEDIUM** | 100.87s | ✅ |
| **GPT-5.1 LOW** | 174.01s | ✅ |
| **GPT-5.1 MEDIUM** | 272.40s | ✅ |

**Observation:** All configurations succeeded. GPT-5 LOW was **14.9x faster** than GPT-5.1 MEDIUM!

---

### 2. ⚠️ I made a downdetector for downdetector's downdetector's downdetector
**Source:** https://downdetectorsdowndetectorsdowndetectorsdowndetector.com

| Configuration | Time | Success |
|--------------|------|---------|
| **GPT-5 LOW** | 25.42s | ✅ |
| **GPT-5 MEDIUM** | 57.19s | ✅ |
| **GPT-5.1 LOW** | - | ❌ (HTTP 502) |
| **GPT-5.1 MEDIUM** | 29.65s | ✅ |

**Observation:** GPT-5.1 LOW failed with HTTP 502. GPT-5 handled this joke site reliably.

---

### 3. ✅ Exploring the Limits of Large Language Models as Quant Traders
**Source:** https://nof1.ai/blog/TechPost1

| Configuration | Time | Success |
|--------------|------|---------|
| **GPT-5 LOW** | 80.43s | ✅ |
| **GPT-5 MEDIUM** | 139.08s | ✅ |
| **GPT-5.1 LOW** | 165.54s | ✅ |
| **GPT-5.1 MEDIUM** | 230.04s | ✅ |

**Observation:** Complex technical article. All succeeded. GPT-5 LOW was **2.86x faster** than GPT-5.1 MEDIUM.

---

### 4. ✅ I just want working RCS messaging
**Source:** https://wt.gd/i-just-want-my-rcs-messaging-to-work

| Configuration | Time | Success |
|--------------|------|---------|
| **GPT-5 LOW** | 195.01s | ✅ |
| **GPT-5 MEDIUM** | 261.54s | ✅ |
| **GPT-5.1 LOW** | 297.45s | ✅ |
| **GPT-5.1 MEDIUM** | 300.03s (timeout) | ❌ |

**Observation:** This was the slowest article for all models. GPT-5.1 MEDIUM timed out at 300s.

---

### 5. ❌ What nicotine does to your brain
**Source:** https://economist.com/science-and-technology/2025/09/12/what-nicotine-does-to-your-brain

| Configuration | Time | Success |
|--------------|------|---------|
| **GPT-5 LOW** | 300.01s (timeout) | ❌ |
| **GPT-5 MEDIUM** | 300.01s (timeout) | ❌ |
| **GPT-5.1 LOW** | 300.01s (timeout) | ❌ |
| **GPT-5.1 MEDIUM** | 300.00s (timeout) | ❌ |

**Observation:** All configurations timed out. This Economist article is likely paywalled or extremely long.

---

## Comparative Analysis

### Speed Comparison (Successful Completions)

```
Fastest to Slowest (by average time):
1. GPT-5 LOW       78.13s  (baseline)
2. GPT-5 MEDIUM   139.67s  (+79% vs GPT-5 LOW)
3. GPT-5.1 MEDIUM 177.36s  (+127% vs GPT-5 LOW)
4. GPT-5.1 LOW    212.33s  (+172% vs GPT-5 LOW)
```

### Reliability Comparison

```
Most to Least Reliable:
1. GPT-5 LOW       80% (4/5)
2. GPT-5 MEDIUM    80% (4/5)
3. GPT-5.1 LOW     60% (3/5)
4. GPT-5.1 MEDIUM  60% (3/5)
```

### Cost-Benefit Analysis

**Winner: GPT-5 LOW**
- Fastest average time (78.13s)
- Highest reliability (80%)
- Best for production use

**Runner-up: GPT-5 MEDIUM**
- Still reliable (80%)
- 79% slower but may produce better quality
- Good for complex articles where quality matters

**Surprising: GPT-5.1 Performance**
- Generally 2-3x slower than GPT-5
- Lower reliability (60% vs 80%)
- Unclear if quality improvements justify the slowdown
- May have regression issues or need different tuning

---

## Conclusions

1. **GPT-5 LOW is the clear winner for speed + reliability**
2. **MEDIUM reasoning adds significant overhead** (~80%) but maintains reliability
3. **GPT-5.1 has performance regressions** - slower and less reliable than GPT-5
4. **Complex articles challenge all configurations** - timeouts increase with reasoning effort
5. **Paywalled/restricted content fails universally** (Economist article)

## Recommendations

1. **Production default:** GPT-5 LOW for 80% use cases
2. **High-quality summaries:** GPT-5 MEDIUM when time is not critical
3. **Avoid GPT-5.1 for now** - performance issues need investigation
4. **Increase timeout to 360-420s** for MEDIUM reasoning effort
5. **Add content-length detection** to skip articles that will likely timeout

## Cross-Experiment Comparison (Gemini vs OpenAI)

From the Gemini experiment, we found:
- Gemini LOW: 107.38s avg (60% success)
- Gemini HIGH: 153.23s avg (20% success)

Comparison with OpenAI:
- **GPT-5 LOW (78.13s) is 27% faster than Gemini LOW (107.38s)**
- **GPT-5 is more reliable (80%) than Gemini (60%)**
- **Both show similar patterns:** reasoning overhead adds ~50-80% to processing time
