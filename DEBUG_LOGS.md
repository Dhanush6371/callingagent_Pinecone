# 🔍 Debug Logs Guide

## What Was Added

Minimal debug logs to trace Clover integration issues. All logs are marked with `🔍 DEBUG:` for easy identification.

---

## Log Flow (What to Look For)

When an order is placed via phone call, you'll see this sequence in the logs:

### **1. Agent Level (agent.py)**
```
🔍 DEBUG: Agent save_order_async starting...
🔍 DEBUG: Items payload: [{'name': 'Chicken Biryani', 'price': 12.99, 'quantity': 2}]
```

### **2. Database Level (db.py)**
```
🔍 DEBUG: create_order_with_clover called - phone=+1234567890, items_count=2
🔍 DEBUG: MongoDB save OK, order_id=673abc123...
🔍 DEBUG: CLOVER_ENABLED=True
🔍 DEBUG: Getting Clover client...
🔍 DEBUG: Calling clover_client.create_order...
```

### **3. Clover Client Level (clover.py)**
```
🔍 DEBUG: Clover client initialized - merchant: ZPDJ2RY8K3SA1, base_url: https://sandbox.dev.clover.com
🔍 DEBUG: Clover create_order - phone=+1234567890, items=[...]
🔍 DEBUG: Creating base order...
🔍 DEBUG: Base order created: ABC123XYZ
🔍 DEBUG: Adding 2 items to order...
🔍 DEBUG: Items added successfully
✅ Clover order complete: ABC123XYZ
```

### **4. Back to Database (db.py)**
```
🔍 DEBUG: Clover API returned: ABC123XYZ
✅ Order synced to Clover POS: ABC123XYZ
```

---

## Common Issues and What Logs Will Show

### **Issue 1: Clover Integration Disabled**
**Symptoms:** Order goes to MongoDB but not Clover

**Logs:**
```
🔍 DEBUG: CLOVER_ENABLED=False
🔍 DEBUG: Clover integration DISABLED - check .env file
```

**Solution:** 
- Check if `clover.py` import failed
- Verify `.env` file has Clover credentials

---

### **Issue 2: Missing Credentials**
**Symptoms:** Error on startup or when creating order

**Logs:**
```
🔍 DEBUG: CLOVER_MERCHANT_ID not found in environment
```
OR
```
🔍 DEBUG: CLOVER_ACCESS_TOKEN not found in environment
```

**Solution:**
Add to `.env` file:
```env
CLOVER_MERCHANT_ID=ZPDJ2RY8K3SA1
CLOVER_ACCESS_TOKEN=2df084bb-f8dc-6ace-8526-3a2dc206db3b
CLOVER_BASE_URL=https://sandbox.dev.clover.com
```

---

### **Issue 3: Clover API Error**
**Symptoms:** Order creates but items don't sync

**Logs:**
```
🔍 DEBUG: Base order created: ABC123XYZ
Failed to add items to Clover order ABC123XYZ
🔍 DEBUG: Clover traceback: [error details]
```

**Solution:** Check traceback for specific API error

---

### **Issue 4: Network/Timeout**
**Symptoms:** Long delay then failure

**Logs:**
```
⚠️ Clover sync error: TimeoutError
🔍 DEBUG: Traceback: [timeout details]
```

**Solution:** Check network connection, increase timeout

---

## How to View Logs

### **Development Mode:**
Logs appear in terminal where you run the agent

### **Production Mode:**
Set `ENVIRONMENT=production` in `.env` to reduce log verbosity

---

## Removing Debug Logs

When debugging is complete, search for `🔍 DEBUG:` in:
- `agent.py`
- `db.py`
- `clover.py`

Remove all lines containing this marker.

**Quick command:**
```bash
# Find all debug logs
grep -n "🔍 DEBUG:" agent.py db.py clover.py
```

---

## Testing with Debug Logs

### **Test 1: Run Test Script**
```bash
python test_clover_integration.py
```

Watch logs for the complete flow.

### **Test 2: Make Phone Call**
Make a real phone call, place order, watch logs in real-time.

### **Test 3: Check Specific Issue**
Look for where the log flow stops:
- Stops at "CLOVER_ENABLED=False" → Credentials issue
- Stops at "Getting Clover client" → Import/initialization issue
- Stops at "Creating base order" → API connection issue
- Stops at "Adding items" → Item format issue

---

## Quick Troubleshooting

**No logs appear?**
- Check log level isn't set too high
- Verify logger name matches

**Logs stop midway?**
- Exception was caught and logged with traceback
- Check the last `🔍 DEBUG:` line to see where it stopped

**Success logs appear but no order in Clover?**
- Check Clover Dashboard filters (Open vs Paid)
- Verify merchant ID matches
- Refresh dashboard page

---

## Performance Impact

These debug logs are:
- ✅ **Minimal** - Only 10-15 extra log lines per order
- ✅ **Fast** - Logging is async, no blocking
- ✅ **Removable** - All marked with 🔍 DEBUG: for easy removal

**Estimated latency:** < 5ms total (negligible)

---

## Next Steps

1. **Make a test phone call**
2. **Watch the logs** as they appear
3. **Find where it stops** in the flow
4. **Share the logs** with me if you need help
5. **Remove debug logs** once issue is resolved

