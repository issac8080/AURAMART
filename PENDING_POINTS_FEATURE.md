# 💎 Pending AuraPoints Feature

## Overview

AuraPoints are now added to the wallet **immediately** when an order is placed, but they remain in "pending" status until the order is delivered. This gives customers instant visibility of their rewards while maintaining the delivery requirement for activation.

---

## 🎯 How It Works

### 1. Order Placement
- Customer places order
- **AuraPoints immediately added** to wallet
- Status: **"Pending"**
- Visible in wallet but **not usable yet**

### 2. Order Delivery
- Order status changes to "Delivered" or "Picked Up"
- **AuraPoints automatically activated**
- Status changes: **"Pending" → "Active"**
- Now **usable** for purchases

### 3. Wallet Display
- **Balance**: Only active points (usable)
- **Pending**: Points waiting for delivery
- **Total Earned**: All points (active + pending)

---

## 📊 Status Flow

```
Order Placed
    ↓
[PENDING] ← Points visible but not usable
    ↓
Order Delivered/Picked Up
    ↓
[ACTIVE] ← Points now usable
    ↓
30 days later
    ↓
[EXPIRED] ← Points removed
```

---

## 🎨 UI Changes

### Wallet Page

**Balance Card:**
- Shows only **active** (usable) points
- New **"Pending" badge** in blue
- Shows amount pending delivery

**Transaction List:**
- Pending transactions have **blue background**
- Badge: "Pending Delivery" with clock icon
- Active transactions show expiry date
- Color coding:
  - Blue = Pending
  - Green = Active
  - Gray = Expired

### Example Display:
```
┌─────────────────────────────────────┐
│ Wallet Balance                      │
│ ₹250.00 (Active)                    │
├─────────────────────────────────────┤
│ ⏰ ₹140 pending                     │
│ Will be available after delivery    │
└─────────────────────────────────────┘

Transactions:
┌─────────────────────────────────────┐
│ 🎁 7% AuraPoints on order ORD-123  │
│ Jan 30, 2026 | ⏰ Pending Delivery  │
│                          +₹140.00   │
└─────────────────────────────────────┘
```

---

## 🔧 Technical Implementation

### Backend Changes

**1. Transaction Status Field:**
```python
class WalletTransaction:
    status: str = "active"  # "pending", "active", "expired"
```

**2. New Functions:**
```python
add_pending_points(user_id, order_id, total)
# Called when order is placed
# Adds transaction with status="pending"
# Does NOT add to balance

activate_pending_points(order_id)
# Called when order is delivered
# Changes status to "active"
# Adds amount to balance
```

**3. Order Creation:**
```python
def create_order(...):
    # ... create order ...
    add_pending_points(user_id, order_id, total)
    # Points immediately visible
```

**4. Order Completion:**
```python
def update_order_status(order_id, status):
    if status in [DELIVERED, PICKED_UP]:
        activate_pending_points(order_id)
        # Points now usable
```

### Frontend Changes

**1. Summary Type:**
```typescript
type Summary = {
  balance: number;          // Active only
  pending_points: number;   // New field
  total_earned: number;     // Active + Pending
  expiring_soon: number;
}
```

**2. Pending Display:**
```tsx
{summary.pending_points > 0 && (
  <div className="bg-blue-500/10">
    <Clock /> {formatPrice(summary.pending_points)} pending
    <p>Will be available after order delivery</p>
  </div>
)}
```

**3. Transaction Styling:**
```tsx
className={
  txn.status === "pending" 
    ? "bg-blue-500/5 border-blue-500/20" 
    : "bg-muted/50"
}
```

---

## 🧪 Testing

### Test Case 1: Place Order
```
1. Add items to cart (₹2,000)
2. Go to checkout
3. Place order
4. Immediately go to /wallet
5. Should see:
   - Balance: ₹0 (if new user)
   - Pending: ₹140 (7% of ₹2,000)
   - Transaction with "Pending Delivery" badge
```

### Test Case 2: Complete Order
```
1. Place order (₹1,500)
2. Check wallet → See ₹105 pending
3. Go to /store-scanner
4. Complete pickup
5. Refresh wallet
6. Should see:
   - Balance: ₹105 (now active)
   - Pending: ₹0
   - Transaction shows expiry date
```

### Test Case 3: Multiple Orders
```
1. Place order 1 (₹1,000) → ₹70 pending
2. Place order 2 (₹2,000) → ₹140 pending
3. Wallet shows:
   - Balance: ₹0
   - Pending: ₹210
4. Complete order 1
5. Wallet shows:
   - Balance: ₹70
   - Pending: ₹140
6. Complete order 2
7. Wallet shows:
   - Balance: ₹210
   - Pending: ₹0
```

---

## 💡 Benefits

### For Customers:
- **Instant gratification** - See rewards immediately
- **Transparency** - Know exactly what you'll earn
- **Motivation** - Encourages order completion
- **Trust** - Clear status tracking

### For Business:
- **Reduced returns** - Customers want to activate points
- **Order completion** - Incentive to receive order
- **Engagement** - Customers check wallet more often
- **Loyalty** - Visible rewards build loyalty

---

## 📈 User Psychology

### Before (Old System):
```
Order → Delivery → Surprise! Points added
❌ No visibility
❌ No anticipation
❌ Forgotten about
```

### After (New System):
```
Order → See pending points → Anticipation → Delivery → Points activated!
✅ Immediate visibility
✅ Creates anticipation
✅ Encourages completion
✅ Memorable experience
```

---

## 🎯 Business Logic

### Balance Calculation:
```python
# Only active points count toward balance
balance = sum(txn.amount for txn in transactions 
              if txn.status == "active" and not txn.is_expired)
```

### Pending Points:
```python
# Shown separately
pending = sum(txn.amount for txn in transactions 
              if txn.status == "pending")
```

### Total Earned:
```python
# Includes both active and pending
total_earned = sum(txn.amount for txn in transactions 
                   if txn.type == "credit")
```

---

## 🔒 Security & Validation

### Prevents Double Credit:
```python
# Check if points already exist for order
for txn in wallet.transactions:
    if txn.order_id == order_id:
        # Already exists, just activate
        return activate_pending_points(order_id)
```

### Activation Rules:
- Only pending points can be activated
- Points linked to specific order ID
- Activation only on delivery/pickup status
- Cannot activate twice

---

## 🎨 Visual Design

### Color Scheme:
- **Blue** = Pending (waiting)
- **Green** = Active (usable)
- **Amber** = Expiring soon
- **Gray** = Expired

### Icons:
- **Clock** (⏰) = Pending/Expiring
- **Gift** (🎁) = AuraPoints
- **Sparkles** (✨) = Wallet/Active

### Badges:
- "Pending Delivery" - Blue with clock
- "Expires [date]" - Outline with clock
- "Expired" - Gray outline

---

## 📝 API Response Example

### Get Wallet:
```json
{
  "wallet": {
    "balance": 250.00,
    "total_earned": 390.00,
    "transactions": [...]
  },
  "summary": {
    "balance": 250.00,
    "pending_points": 140.00,
    "active_points": 250.00,
    "expiring_soon": 50.00
  }
}
```

### Transaction:
```json
{
  "id": "TXN-ABC123",
  "amount": 140.00,
  "type": "credit",
  "source": "aurapoints",
  "status": "pending",
  "order_id": "ORD-XYZ789",
  "description": "7% AuraPoints on order ORD-XYZ789",
  "expires_at": "2026-02-28T12:00:00",
  "created_at": "2026-01-30T12:00:00"
}
```

---

## 🚀 Summary

The pending points feature provides:
- ✅ **Immediate visibility** of rewards
- ✅ **Clear status tracking** (pending → active)
- ✅ **Better UX** with anticipation
- ✅ **Accurate balance** (only usable points)
- ✅ **Encourages completion** of orders
- ✅ **Builds trust** through transparency

**Restart backend to apply changes:**
```powershell
cd backend
# Press Ctrl+C
uvicorn app.main:app --reload --port 8000
```

Now customers see their AuraPoints immediately! 🎉
