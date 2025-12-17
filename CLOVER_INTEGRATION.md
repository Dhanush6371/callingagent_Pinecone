# Clover POS Integration Guide

## 🎉 Overview

Your restaurant phone ordering system now automatically syncs orders to **Clover POS**!

When a customer calls and places an order:
1. ✅ Order is saved to **MongoDB** (your database)
2. ✅ Order is automatically sent to **Clover POS** (restaurant system)
3. ✅ Restaurant staff sees the order on their Clover device

---

## 📁 New Files Added

### 1. `clover.py`
The Clover API client that handles all communication with Clover POS.

**Features:**
- Create orders in Clover
- Add line items (dishes) to orders
- Handle authentication with Bearer tokens
- Error handling and logging

### 2. `test_clover_integration.py`
Test script to verify the integration works.

### 3. `CLOVER_INTEGRATION.md`
This documentation file.

---

## 🔧 Setup Instructions

### Step 1: Add Clover Credentials to `.env`

Open your `.env` file and add these lines:

```env
# Clover POS Configuration
CLOVER_MERCHANT_ID=ZPDJ2RY8K3SA1
CLOVER_ACCESS_TOKEN=2df084bb-f8dc-6ace-8526-3a2dc206db3b
CLOVER_BASE_URL=https://sandbox.dev.clover.com
```

**For Production (when ready):**
```env
# Change these for production
CLOVER_BASE_URL=https://api.clover.com
CLOVER_ACCESS_TOKEN=<production_token_from_oauth>
```

---

### Step 2: Test the Integration

Run the test script to verify everything works:

```powershell
python test_clover_integration.py
```

**Expected Output:**
```
✅ Connected to Clover POS
✅ Order created successfully!
✅ Clover Order ID: ABC123XYZ
🎉 All tests passed! Clover integration is ready!
```

---

### Step 3: Verify in Clover Dashboard

After running the test:
1. Go to: https://sandbox.dev.clover.com/home/orders
2. You should see the test orders appear!

---

## 🚀 How It Works

### Order Flow (Automatic)

```
Customer Calls
      ↓
AI Agent Takes Order
      ↓
create_order() function called
      ↓
      ├─→ Save to MongoDB (always happens)
      └─→ Sync to Clover POS (automatic)
      ↓
Order appears on Clover device!
```

### Code Changes

#### 1. `db.py` - New Method: `create_order_with_clover()`

```python
# Old way (MongoDB only)
result = db_driver.create_order(phone, items, name, address)

# New way (MongoDB + Clover POS)
result = await db_driver.create_order_with_clover(phone, items, name, address)
```

#### 2. `agent.py` - Updated to Use Clover Integration

The `create_order` tool in your agent now automatically syncs to Clover:

```python
# In agent.py - line 106-108
result = await db_driver.create_order_with_clover(
    final_phone, items_payload, name, address
)
```

---

## 📊 What Data is Synced

### From Your System → Clover POS

| Field | Description | Example |
|-------|-------------|---------|
| **Phone** | Customer phone number | `+1234567890` |
| **Name** | Customer name | `John Doe` |
| **Items** | Ordered dishes | `Chicken Biryani x2` |
| **Prices** | Item prices | `$12.99` → `1299` cents |
| **Quantities** | Item quantities | `2` |
| **Note** | Order note with phone | `Phone: +1234567890` |

### Clover POS Response → Your Database

After syncing to Clover, your MongoDB order is updated with:

```json
{
  "_id": "mongodb_id_here",
  "phone": "+1234567890",
  "items": [...],
  "clover_order_id": "ABC123XYZ",  // ← Added after Clover sync
  "status": "confirmed",
  "created_at": "2024-11-05T..."
}
```

---

## 🛡️ Error Handling

### What Happens if Clover is Down?

**✅ Your system keeps working!**

1. Order is **always saved to MongoDB first**
2. If Clover sync fails, you see a warning in logs
3. Customer doesn't experience any issues
4. Restaurant can manually enter the order later

```
✅ Order saved to MongoDB
⚠️ Failed to sync to Clover (order saved in MongoDB)
```

---

## 🧪 Testing Scenarios

### Test 1: Normal Order (Happy Path)
```bash
python test_clover_integration.py
```
Expected: ✅ Order in both MongoDB and Clover

### Test 2: Clover API Down (Fault Tolerance)
```bash
# Temporarily set wrong token in .env
CLOVER_ACCESS_TOKEN=invalid_token

python test_clover_integration.py
```
Expected: ✅ Order saved to MongoDB, ⚠️ Clover sync fails (graceful)

### Test 3: Real Phone Call
Make a test call to your system and place an order.
Expected: ✅ Order appears in Clover Dashboard

---

## 📝 Price and Quantity Format Conversion

**Important:** Clover has specific format requirements:

Your system automatically converts:

```python
# Your format
{"name": "Biryani", "price": 12.99, "quantity": 2}

# Converted to Clover format
{"name": "Biryani", "price": 1299, "unitQty": 2000}
                            ↑                  ↑
                    12.99 × 100 = 1299 cents   2 × 1000 = 2000 units
```

**Conversion Rules:**
- **Prices**: Multiply by 100 (dollars → cents)
  - $12.99 → 1299 cents
- **Quantities**: Multiply by 1000 (Clover unit format)
  - 2 items → 2000 units
  - 1 item → 1000 units

---

## 🔐 Security Best Practices

### Sandbox vs Production

| Environment | Base URL | Token Type |
|-------------|----------|------------|
| **Sandbox** (Testing) | `https://sandbox.dev.clover.com` | Test API Token |
| **Production** (Live) | `https://api.clover.com` | OAuth Token |

### Token Security

✅ **DO:**
- Keep tokens in `.env` file (not in code)
- Add `.env` to `.gitignore`
- Use different tokens for sandbox/production

❌ **DON'T:**
- Commit tokens to GitHub
- Share tokens publicly
- Use production tokens in development

---

## 🚀 Going to Production

When ready to deploy with real Clover merchants:

### 1. Implement OAuth Flow

For production, you need OAuth (not test tokens):

```python
# See CLOVER_INTEGRATION.md for OAuth implementation
# Or contact Clover support for OAuth setup
```

### 2. Update Environment Variables

```env
CLOVER_BASE_URL=https://api.clover.com
CLOVER_ACCESS_TOKEN=<oauth_token_from_production>
CLOVER_MERCHANT_ID=<real_merchant_id>
```

### 3. Test with Real Merchant

Before going live:
1. Create test orders
2. Verify they appear on real Clover device
3. Test edge cases (no phone, special characters, etc.)

---

## 🐛 Troubleshooting

### Issue: "CLOVER_MERCHANT_ID environment variable not set"

**Solution:** Add Clover credentials to your `.env` file

```env
CLOVER_MERCHANT_ID=ZPDJ2RY8K3SA1
CLOVER_ACCESS_TOKEN=2df084bb-f8dc-6ace-8526-3a2dc206db3b
CLOVER_BASE_URL=https://sandbox.dev.clover.com
```

---

### Issue: "401 Unauthorized"

**Solution:** Token is invalid or expired

1. Go to Clover Dashboard: https://sandbox.dev.clover.com
2. Setup → API Tokens
3. Create new token
4. Update `.env` file with new token

---

### Issue: "403 Forbidden"

**Solution:** Token doesn't have required permissions

1. Go to App Settings
2. Requested Permissions → Edit
3. Add: Orders (Read/Write), Customers (Read/Write), Merchant (Read)
4. Regenerate API token

---

### Issue: Orders not appearing in Clover Dashboard

**Solution:** Check multiple things

1. **Verify token works:**
   ```bash
   python test_clover_integration.py
   ```

2. **Check logs:**
   Look for "✅ Order synced to Clover POS" in your logs

3. **Verify merchant ID:**
   Make sure `CLOVER_MERCHANT_ID` matches your dashboard

4. **Check Clover Dashboard:**
   https://sandbox.dev.clover.com/home/orders

---

## 📞 Support

### Clover Documentation
- API Reference: https://docs.clover.com/reference/api-reference-overview
- Developer Portal: https://www.clover.com/developers

### Your Implementation
- Clover Client: `clover.py`
- Database Integration: `db.py` (line 129-184)
- Agent Integration: `agent.py` (line 106-108)

---

## ✅ Integration Checklist

- [x] Created `clover.py` module
- [x] Updated `db.py` with Clover sync
- [x] Updated `agent.py` to use Clover integration
- [x] Added test script
- [ ] **TODO:** Add Clover credentials to `.env`
- [ ] **TODO:** Run `python test_clover_integration.py`
- [ ] **TODO:** Verify orders appear in Clover Dashboard
- [ ] **TODO:** Test with real phone call

---

## 🎉 That's It!

Your phone ordering system now automatically syncs to Clover POS! 🚀

**Next Steps:**
1. Add credentials to `.env` file
2. Run test script
3. Make a test phone call
4. Check Clover Dashboard

Questions? Check the troubleshooting section or review the code in `clover.py`.

