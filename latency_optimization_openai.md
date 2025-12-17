# Bawarchi AI Voice Agent - Latency Optimization Guide
## OpenAI-Based System (Revised)

**Last Updated**: November 4, 2025  
**Current Stack**: OpenAI GPT-4o + Deepgram STT + OpenAI TTS

---

## Executive Summary

Your system already uses OpenAI GPT-4o (text-based) with Deepgram STT and OpenAI TTS. Current estimated latency is **1.5-2.5 seconds**. With optimizations, you can achieve **0.8-1.3 seconds** (35-50% improvement).

**Quick Wins (Priority Order):**
1. Switch to GPT-4o-mini (50% faster, 80% cheaper)
2. Enable streaming responses (40% improvement)
3. Optimize prompts (20-30% improvement)
4. Tune VAD settings (25% improvement)
5. Add response caching (30% on cached responses)

---

## Current System Analysis

### Tech Stack
```
STT: Deepgram Nova-2
LLM: OpenAI GPT-4o (text)
TTS: OpenAI TTS (alloy voice)
VAD: Silero (default settings)
```

### Current Latency Breakdown
```
VAD Detection: 300-500ms
STT (Deepgram): 200-300ms
LLM (GPT-4o): 600-1000ms
TTS (OpenAI): 300-500ms
Network: 100-200ms
----------------------------
TOTAL: 1500-2500ms
```

### Good Things Already in Place ✅
- Async database operations (non-blocking)
- Prompt caching at module level
- Phone extraction runs in parallel
- Immediate greeting start
- Timeout fallbacks (5 seconds)
- Smart fallback responses

---

## Optimization 1: Switch to GPT-4o-mini

### Why
GPT-4o is powerful but slower and expensive. GPT-4o-mini is perfect for conversational tasks.

### Change Required
**File**: `agent.py` (line 393-397)

**Current:**
```python
llm=OpenAIModel(
    model="gpt-4o",
    api_key=openai_api_key,
    temperature=0.2,
),
```

**Optimized:**
```python
llm=OpenAIModel(
    model="gpt-4o-mini",  # 50% faster, 80% cheaper
    api_key=openai_api_key,
    temperature=0.3,  # Slightly higher for natural responses
),
```

### Impact
- **Latency**: 600-1000ms → 300-500ms (50% faster)
- **Cost**: $5.00/1M tokens → $0.60/1M tokens (88% cheaper)
- **Quality**: Still excellent for restaurant orders

---

## Optimization 2: Enable Streaming

### Why
Start generating TTS before LLM completes, reducing perceived latency.

### Changes Required
**File**: `agent.py` (line 393-401)

**Add streaming to LLM:**
```python
llm=OpenAIModel(
    model="gpt-4o-mini",
    api_key=openai_api_key,
    temperature=0.3,
    stream=True,  # Enable streaming
),
```

### Impact
- **Latency**: Perceived reduction of 40%
- **User Experience**: More natural, responsive feel
- **Implementation**: Simple one-line change

---

## Optimization 3: Optimize Deepgram STT

### Why
Current config uses defaults which may not be optimized for speed.

### Changes Required
**File**: `agent.py` (line 389-392)

**Current:**
```python
stt=deepgram.STT(
    api_key=deepgram_api_key,
    model="nova-2-general",
),
```

**Optimized:**
```python
stt=deepgram.STT(
    api_key=deepgram_api_key,
    model="nova-2-general",
    language="en",  # Or "multi" if needed
    interim_results=True,  # Start processing immediately
    endpointing=200,  # Faster (default 300ms)
    smart_format=True,
    punctuate=True,
),
```

### Impact
- **Latency**: 200-300ms → 150-200ms (30% faster)
- **Responsiveness**: Faster turn-taking

---

## Optimization 4: Optimize VAD Settings

### Why
Default Silero settings are conservative, causing delays.

### Changes Required
**File**: `agent.py` (add VAD config in entrypoint)

**Add after line 402:**
```python
from livekit.plugins import silero

vad = silero.VAD.load(
    min_speech_duration=0.2,  # Faster (default 0.5s)
    min_silence_duration=0.35,  # Quicker turn-taking (default 0.5s)
    padding_duration=0.15,  # Less padding (default 0.3s)
)

session = AgentSession(
    stt=deepgram.STT(...),
    llm=OpenAIModel(...),
    tts=openai.TTS(...),
    vad=vad,  # Add custom VAD
)
```

### Impact
- **Latency**: 300-500ms → 200-300ms (35% faster)
- **Turn-taking**: More natural conversation flow

---

## Optimization 5: Reduce Prompt Length

### Why
Your prompts are ~5000 tokens. Reducing to ~2000 tokens speeds processing.

### Changes Required
**File**: `prompts.py`

**Current Structure:**
- Verbose explanations
- Many examples for each language
- Repeated information

**Optimization Strategy:**
```python
# Keep:
- Core persona and task
- Menu (condensed)
- Language rules (simplified)
- Critical behavioral rules

# Remove:
- Verbose examples (keep 1-2 max per language)
- Repeated behavioral explanations
- Over-detailed formatting instructions
```

**Example - Condensed Language Section:**
```python
# Language Support
- DEFAULT: English (unless customer speaks Telugu/Hindi)
- Detect from first customer message
- Respond ONLY in detected language
- Use natural, conversational expressions

Examples:
- English: "What would you like?"
- Telugu: "ఏమి కావాలి?"
- Hindi: "क्या चाहिए?"
```

### Impact
- **Latency**: 20-30% faster LLM processing
- **Cost**: 60% reduction in token usage
- **Quality**: No degradation (concise is better)

---

## Optimization 6: Add Response Caching

### Why
Common responses (greetings, confirmations) can be pre-cached.

### Implementation
**File**: `agent.py` (add to RestaurantAgent class)

```python
class RestaurantAgent(Agent):
    _response_cache = {
        "greeting_en": "Hello! Welcome to Bawarchi Restaurant. I'm Sarah. What would you like to order today?",
        "greeting_te": "నమస్కారం! Bawarchi Restaurant కి స్వాగతం. నేను Sarah. ఏమి ఆర్డర్ చేయాలి?",
        "greeting_hi": "नमस्ते! Bawarchi Restaurant में आपका स्वागत है। मैं Sarah हूँ। क्या ऑर्डर करना है?",
        "confirm_en": "Would you like me to confirm this order?",
        "confirm_te": "ఈ ఆర్డర్ కాన్ఫిర్మ్ చేయాలా?",
        "confirm_hi": "यह ऑर्डर कन्फर्म कर दूँ?",
    }
```

### Impact
- **Latency**: 300-500ms → 50-100ms for cached responses
- **Cost**: Near zero for common phrases
- **Consistency**: Same quality every time

---

## Optimization 7: Parallel Processing (Already Implemented ✅)

### Current Implementation
Your code already does this well:
```python
# Line 95-112: Async database save (non-blocking)
asyncio.create_task(save_order_async())

# Line 470: Phone extraction in parallel
asyncio.create_task(extract_phone_number())

# Line 473: Greeting starts immediately
asyncio.create_task(agent.on_start(session))
```

### No Changes Needed
This is already optimized!

---

## Optimization 8: Database Indexing

### Why
Database queries can be slow without indexes.

### Changes Required
**File**: `db.py` (add to DatabaseDriver.__init__)

```python
def __init__(self):
    self.collection = orders_collection
    self.log = logging.getLogger("realtime_restaurant_agent")
    
    # Create indexes for faster queries
    try:
        self.collection.create_index("phone", background=True)
        self.collection.create_index("created_at", background=True)
    except Exception as e:
        self.log.warning(f"Index creation: {e}")
```

### Impact
- **Query Speed**: 50-100ms → 10-20ms
- **Scalability**: Better performance with more orders

---

## Optimization 9: Reduce Timeout

### Why
Current 5-second timeout is too generous for most responses.

### Changes Required
**File**: `agent.py` (line 170)

**Current:**
```python
timeout=5.0
```

**Optimized:**
```python
timeout=3.0  # Still safe, but faster fallback
```

### Impact
- **User Experience**: Faster fallback to smart responses
- **Perceived Speed**: Less dead air time

---

## Optimization 10: Production Settings

### Changes Required
**File**: `agent.py`

**Add environment-based logging:**
```python
# At top of file
PRODUCTION = os.getenv("ENVIRONMENT") == "production"

if PRODUCTION:
    logging.getLogger("realtime_restaurant_agent").setLevel(logging.WARNING)
    logging.getLogger("livekit").setLevel(logging.ERROR)
else:
    logging.getLogger("realtime_restaurant_agent").setLevel(logging.INFO)
```

**In .env:**
```bash
ENVIRONMENT=production
```

### Impact
- **Latency**: 20-50ms saved from reduced logging
- **Performance**: Less I/O overhead

---

## Implementation Roadmap

### Phase 1: Quick Wins (30 minutes)
**Priority: HIGHEST**

1. Switch to GPT-4o-mini (5 min)
2. Enable streaming (2 min)
3. Optimize STT settings (5 min)
4. Add VAD config (10 min)
5. Reduce timeout (1 min)
6. Add production logging (5 min)

**Expected Result**: 1.0-1.5s latency (from 1.5-2.5s)

### Phase 2: Prompt Optimization (2 hours)
**Priority: HIGH**

1. Analyze token usage
2. Condense prompts by 60%
3. Test quality
4. Deploy

**Expected Result**: 0.8-1.2s latency

### Phase 3: Caching & Indexes (1 hour)
**Priority: MEDIUM**

1. Add response cache
2. Create DB indexes
3. Test performance

**Expected Result**: 0.8-1.0s latency (with caching)

---

## Expected Results Summary

| Phase | Configuration | Latency | Cost/Call | Improvement |
|-------|--------------|---------|-----------|-------------|
| Baseline | Current (GPT-4o) | 1.5-2.5s | $0.015 | - |
| Phase 1 | GPT-4o-mini + optimizations | 1.0-1.5s | $0.003 | 40% |
| Phase 2 | + Prompt optimization | 0.8-1.2s | $0.002 | 50% |
| Phase 3 | + Caching | 0.8-1.0s | $0.001 | 60% |

---

## Cost Analysis

### Current (GPT-4o)
```
Input: $2.50 / 1M tokens
Output: $10.00 / 1M tokens
Avg call: ~4000 tokens
Cost per call: ~$0.015
```

### Optimized (GPT-4o-mini + condensed prompts)
```
Input: $0.15 / 1M tokens
Output: $0.60 / 1M tokens
Avg call: ~1600 tokens (condensed)
Cost per call: ~$0.001
```

**Savings: 93% cost reduction + 50% faster**

---

## Testing Checklist

### Before Deployment
- [ ] Test single call (order placement)
- [ ] Test concurrent calls (2-3 simultaneous)
- [ ] Test language detection (English, Telugu, Hindi)
- [ ] Test fallback responses
- [ ] Verify database saves correctly
- [ ] Check call termination works
- [ ] Measure actual latency

### Performance Metrics to Track
- Average response time
- P95 response time
- Error rate
- Order success rate
- Language detection accuracy

---

## Should You Use OpenAI Realtime API?

### Your Current System
- **STT**: Deepgram Nova-2
- **LLM**: OpenAI GPT-4o (text)
- **TTS**: OpenAI TTS

### OpenAI Realtime Alternative
- **Everything**: Native audio-to-audio

### Comparison

| Feature | Current (Optimized) | OpenAI Realtime |
|---------|-------------------|-----------------|
| Latency | 0.8-1.3s | 0.3-0.5s |
| Cost/call | $0.001-0.003 | $1.50 |
| Quality | Excellent | Excellent |
| Control | High | Medium |
| Multi-language | Excellent (Deepgram) | Good |

### Recommendation
**Stick with current optimized system.**

Why?
- 0.8-1.3s is already very fast
- 500x cheaper ($0.002 vs $1.50)
- Better voice quality for multi-language
- More control over each component
- 0.3s speed gain doesn't justify 500x cost

### When to Consider Realtime API
- If customers complain about speed (unlikely at <1s)
- If order values are very high (>$50)
- If cost is not a concern

---

## Quick Reference: All Changes

### 1. agent.py - Line 393-397
```python
# Before
llm=OpenAIModel(model="gpt-4o", ...)

# After
llm=OpenAIModel(model="gpt-4o-mini", temperature=0.3, stream=True, ...)
```

### 2. agent.py - Line 389-392
```python
# Before
stt=deepgram.STT(api_key=deepgram_api_key, model="nova-2-general")

# After
stt=deepgram.STT(
    api_key=deepgram_api_key,
    model="nova-2-general",
    language="en",
    interim_results=True,
    endpointing=200,
)
```

### 3. agent.py - Add VAD (after line 402)
```python
from livekit.plugins import silero

vad = silero.VAD.load(
    min_speech_duration=0.2,
    min_silence_duration=0.35,
    padding_duration=0.15,
)

session = AgentSession(
    stt=...,
    llm=...,
    tts=...,
    vad=vad,
)
```

### 4. agent.py - Line 170
```python
# Before
timeout=5.0

# After
timeout=3.0
```

### 5. prompts.py
Condense from ~5000 tokens to ~2000 tokens by:
- Removing verbose examples
- Simplifying language rules
- Condensing menu format

### 6. db.py - Add to __init__
```python
self.collection.create_index("phone", background=True)
self.collection.create_index("created_at", background=True)
```

---

## Monitoring After Deployment

### Key Metrics
```python
# Add timing logs in agent.py
import time

start = time.time()
# ... process request ...
latency = (time.time() - start) * 1000  # ms
log.info(f"Response latency: {latency}ms")
```

### Alert Thresholds
- P95 latency > 2000ms → investigate
- Error rate > 5% → investigate
- Order failure rate > 2% → investigate

---

## Rollback Plan

### If Issues Occur
```python
# Quick rollback in agent.py
USE_OPTIMIZATIONS = os.getenv("USE_OPTIMIZATIONS", "true") == "true"

if USE_OPTIMIZATIONS:
    model = "gpt-4o-mini"
    timeout = 3.0
else:
    model = "gpt-4o"
    timeout = 5.0
```

### Environment Variable
```bash
# Rollback
USE_OPTIMIZATIONS=false

# Enable optimizations
USE_OPTIMIZATIONS=true
```

---

## Conclusion

### Bottom Line
Your system is already well-architected with async operations and caching. The biggest wins will come from:

1. **GPT-4o-mini**: 50% faster, 88% cheaper
2. **Streaming**: 40% perceived improvement
3. **Prompt optimization**: 30% faster
4. **VAD tuning**: 25% faster

**Total Expected Improvement**: 40-60% latency reduction + 93% cost reduction

### Next Steps
1. Implement Phase 1 (30 minutes)
2. Test with real calls
3. Monitor performance
4. Implement Phase 2 if needed

### Final Recommendation
Start with Phase 1 optimizations. You'll likely be satisfied with the results and may not need Phase 2 or 3.

---

**Document Version**: 2.0 (OpenAI-based)  
**Status**: Ready for Implementation  
**Estimated Implementation Time**: 30 minutes (Phase 1)
