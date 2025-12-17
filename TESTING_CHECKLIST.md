# 🧪 Testing Checklist - Clover Integration

## ✅ What to Check After Making a Test Call

### **1. Agent Startup Logs**
Look for this at startup:
```
✅ Should see: 🔍 DEBUG: Clover module imported successfully - integration ENABLED
❌ Bad: 🔍 DEBUG: Clover module import FAILED
```

### **2. During Call - Order Creation**
When you say "I'd like to order [item]", look for these logs:

```
🔍 DEBUG: Agent save_order_async starting...
🔍 DEBUG: Items payload: [{'name': '...', 'price': ..., 'quantity': ...}]
🔍 DEBUG: create_order_with_clover called - phone=+91...
🔍 DEBUG: MongoDB save OK, order_id=...
🔍 DEBUG: CLOVER_ENABLED=True
🔍 DEBUG: Getting Clover client...
🔍 DEBUG: Clover client initialized - merchant: ZPDJ2RY8K3SA1
🔍 DEBUG: Clover create_order - phone=+91..., items=[...]
🔍 DEBUG: Creating base order...
🔍 DEBUG: Base order created: ABC123XYZ
🔍 DEBUG: Adding 2 items to order...
🔍 DEBUG: Items added successfully
✅ Clover order complete: ABC123XYZ
🔍 DEBUG: Clover API returned: ABC123XYZ
✅ Order synced to Clover POS: ABC123XYZ
```

### **3. If NO Debug Logs Appear During Call**

This means the order was NOT placed. Possible reasons:

**A. Conversation Failed**
- Agent didn't understand you
- You hung up before confirming order
- Order was never finalized

**B. Agent Never Called create_order()**
- Check if agent said "Order placed successfully!"
- If agent didn't say this, the order wasn't created

**C. Technical Issue**
- Check MongoDB - is order there?
- If yes → Clover integration issue
- If no → Order was never created by agent

---

## 📋 Complete Test Flow

### **Step 1: Start Agent**
```bash
python agent.py dev
```

**Expected:**
```
✅ 🔍 DEBUG: Clover module imported successfully - integration ENABLED
✅ Agent starts without errors
```

---

### **Step 2: Make Call & Place Order**

**Say this:**
```
"Hello, I'd like to order 2 Mutton Biryani and 1 Chicken Curry"
```

**Agent should:**
1. Confirm items
2. Ask for phone number (if not already captured)
3. Say "Order placed successfully!"

---

### **Step 3: Check Logs**

**Look for:**
- ✅ `🔍 DEBUG: Agent save_order_async starting...` (order creation started)
- ✅ `🔍 DEBUG: MongoDB save OK` (saved to database)
- ✅ `✅ Order synced to Clover POS: ABC123XYZ` (synced to Clover)

**If you DON'T see these logs:**
- Order was never placed
- Agent conversation failed
- Try again with clearer speech

---

### **Step 4: Verify in Systems**

**Check MongoDB:**
```bash
# Your database should have new order
```

**Check Clover Dashboard:**
```
https://sandbox.dev.clover.com/home/orders
Should see new order with your items
```

---

## 🎯 Success Criteria

| Check | Status |
|-------|--------|
| Agent starts without errors | ✅ |
| Clover integration enabled at startup | ✅ |
| Call connects successfully | ✅ |
| Agent understands speech correctly | ✅ |
| Agent confirms order | ✅ |
| Debug logs appear during order | ✅ |
| Order saved to MongoDB | ✅ |
| Order synced to Clover | ✅ |
| Order visible in Clover Dashboard | ✅ |

---

## 🐛 Common Issues

### **Issue: No debug logs during call**
**Cause:** Order was never placed (conversation failed)
**Solution:** Try again, speak clearly, confirm order

### **Issue: "Clover integration DISABLED"**
**Cause:** Missing .env credentials
**Solution:** Add Clover credentials to .env file

### **Issue: MongoDB has order, Clover doesn't**
**Cause:** Clover sync failed (check error logs)
**Solution:** Look for "⚠️ Clover sync error" in logs

### **Issue: Agent doesn't understand speech**
**Cause:** STT configuration issue
**Solution:** Use default STT settings (minimal parameters)

---

## 📝 What to Share for Debugging

If something doesn't work, share:

1. **Startup logs** (first 10-20 lines)
2. **Full call logs** (entire conversation)
3. **Any error messages** (lines with ERROR or WARNING)
4. **Confirmation:**
   - Is order in MongoDB? (yes/no)
   - Is order in Clover? (yes/no)
   - Did agent say "Order placed successfully"? (yes/no)

---

## ✅ Quick Test Command

```bash
# Test Clover directly (bypasses agent)
python test_clover_integration.py
```

This will tell you if Clover API is working independently of the agent.

