# What the Agent (LLM) Receives from Menu Search

## Answer: **Only Top 5 Items** (NOT the entire menu)

## Detailed Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: Customer Query                              │
│  Customer: "chicken biryani"                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 2: Hierarchical Filtering                     │
│  Filter Applied:                                                 │
│    section='non_veg' AND sub_section='biryani' AND             │
│    protein='chicken'                                            │
│                                                                  │
│  Search Space: 8-10 items (filtered from 399)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 3: Pinecone Semantic Search                   │
│  Searches within filtered 8-10 items                           │
│  Returns: top_k=5 (top 5 most relevant)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 4: Agent Receives (What LLM Sees)             │
│                                                                  │
│  [                                                               │
│    {                                                             │
│      "id": "nawabi_chicken_biryani",                            │
│      "name": "Nawabi Chicken Biryani",                          │
│      "price": 15.95,                                            │
│      "score": 0.678,                                            │
│      "category": "chicken_biryani"                               │
│    },                                                            │
│    {                                                             │
│      "id": "boneless_chicken_biryani",                          │
│      "name": "Boneless Chicken Biryani",                        │
│      "price": 15.95,                                            │
│      "score": 0.675,                                            │
│      "category": "chicken_biryani"                               │
│    },                                                            │
│    {                                                             │
│      "id": "dil_kush_biryani",                                  │
│      "name": "Dil Kush Biryani",                                │
│      "price": 15.95,                                            │
│      "score": 0.659,                                            │
│      "category": "chicken_biryani"                               │
│    },                                                            │
│    {                                                             │
│      "id": "chicken_tikka_biryani",                             │
│      "name": "Chicken Tikka Biryani",                           │
│      "price": 15.45,                                            │
│      "score": 0.655,                                            │
│      "category": "chicken_biryani"                               │
│    },                                                            │
│    {                                                             │
│      "id": "chicken_dum_biryani",                               │
│      "name": "Chicken Dum Biryani",                             │
│      "price": 15.45,                                            │
│      "score": 0.650,                                            │
│      "category": "chicken_biryani"                               │
│    }                                                             │
│  ]                                                               │
│                                                                  │
│  Total: 5 items only                                            │
│  Token Usage: ~250 tokens (vs ~1,050 for entire menu)          │
└─────────────────────────────────────────────────────────────────┘
```

## Key Points

### 1. **Filtering Happens FIRST**
   - Before semantic search, items are filtered by metadata
   - Example: "chicken biryani" → searches only 8-10 chicken biryani items
   - NOT searching all 399 items

### 2. **Then Semantic Search**
   - Within the filtered 8-10 items, Pinecone does semantic search
   - Finds the most relevant items based on similarity

### 3. **Returns Top 5 Only**
   - `top_k=5` means only top 5 most relevant items
   - Agent receives only these 5 items
   - NOT the entire menu

### 4. **Token Usage**
   ```
   Entire Menu (399 items):     ~1,050 tokens
   Filtered Search (8-10 items): ~100 tokens (search space)
   Top 5 Results:                ~250 tokens (what agent sees)
   
   Savings: 76% reduction!
   ```

## Example: "chicken biryani"

### What Happens:
1. **Filter Applied**: non_veg + biryani + chicken
2. **Search Space**: Only ~8-10 chicken biryani items (not 399)
3. **Semantic Search**: Within those 8-10 items
4. **Top 5 Returned**: Most relevant 5 chicken biryani items
5. **Agent Receives**: Only those 5 items

### What Agent Sees:
```json
[
  {"name": "Nawabi Chicken Biryani", "price": 15.95},
  {"name": "Boneless Chicken Biryani", "price": 15.95},
  {"name": "Dil Kush Biryani", "price": 15.95},
  {"name": "Chicken Tikka Biryani", "price": 15.45},
  {"name": "Chicken Dum Biryani", "price": 15.45}
]
```

**Total: 5 items only** ✅

## Why This is Optimal

1. **Relevant Results**: Only items matching the query
2. **Small Token Usage**: 5 items vs 399 items
3. **Fast Processing**: Agent doesn't need to process irrelevant items
4. **Better Accuracy**: Top 5 most relevant items

## If You Want More Items

You can change `top_k` parameter:

```python
# In agent.py, you could modify:
results = search_menu(query, top_k=10)  # Returns top 10 instead of 5
```

But 5 is usually enough for the agent to find what the customer wants!

## Summary

✅ **Agent receives: Top 5 items only**  
✅ **Filtering happens: Before semantic search**  
✅ **Search space: 8-10 items (not 399)**  
✅ **Token usage: ~250 tokens (not ~1,050)**  
✅ **Result: Fast, accurate, cost-effective**




