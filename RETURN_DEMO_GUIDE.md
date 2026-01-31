# Return & Exchange Demo Guide

## 🎯 Quick Demo Flow

### Step 1: Create an Order
1. Browse products at `http://localhost:3000`
2. Add items to cart
3. Go to checkout
4. Complete order (choose any delivery method)

### Step 2: Mark Order as Delivered (Demo Button)
1. Navigate to **Profile** → **Order History**
2. Click on your order to view details
3. You'll see a **green "Mark as Delivered (Demo)"** button
4. Click it to simulate delivery

**What happens:**
- ✅ Order status changes to "delivered"
- ✅ AuraPoints are calculated and shown
- ✅ **"Return / Exchange" button appears**
- ✅ You get a confirmation about points being credited

### Step 3: Create Return Request
1. After marking as delivered, the **"Return / Exchange"** button is now visible
2. Click the blue **"Return / Exchange"** button
3. Fill out the return form:
   - Select issue type (Physical, Functional, etc.)
   - Describe the problem (min 10 characters)
   - Provide email or phone number
   - Upload photos (optional)
4. Submit the request

**What happens:**
- ✅ AI analyzes your request automatically
- ✅ You get instant decision or manual review
- ✅ Redirected to return details page

### Step 4: View Return Status
1. You'll be redirected to `/returns/{returnId}`
2. View:
   - AI decision (Approved/Rejected)
   - Confidence score
   - Reasoning
   - Status updates

---

## 📍 Where to Find Return Option

### Location 1: Order Details Page
```
Profile → Order History → Click Order → "Return / Exchange" button
```

**Button Visibility:**
- ❌ **NOT visible** for: pending, confirmed, out_for_delivery orders
- ✅ **VISIBLE** for: delivered, picked_up orders

**Demo Shortcut:**
- Use **"Mark as Delivered (Demo)"** button to instantly enable return option

---

## 💎 AuraPoints System

### When Points Are Earned
**Timing:** When order status changes to `delivered` or `picked_up`

**Calculation:**
```
Order Total    | AuraPoints Rate
---------------|----------------
₹0 - ₹499      | 1% cashback
₹500 - ₹999    | 2% cashback
₹1,000 - ₹4,999| 3% cashback
₹5,000 - ₹9,999| 4% cashback
₹10,000+       | 5% cashback
```

**Example:**
- Order total: ₹2,500
- AuraPoints: ₹75 (3%)
- Validity: 30 days

### When Points Are Deducted
**Timing:** When return is approved

**What happens:**
1. Return request submitted
2. AI/Admin approves return
3. AuraPoints earned from that order are deducted from wallet
4. Refund processed (if applicable)

**Important Notes:**
- ⚠️ Users are warned about point deduction when creating return
- ⚠️ Banner on order details shows this information
- ⚠️ Warning on return creation page

---

## 🎨 UI Elements

### Order Details Page

#### 1. AuraPoints Info Banner (Top)
```
┌─────────────────────────────────────────┐
│ 💫 AuraPoints Rewards                   │
│ ✓ Earn up to 5% when delivered         │
│ ✓ Points credited automatically         │
│ ✓ Valid for 30 days                     │
│ ⚠️ Deducted if order returned           │
└─────────────────────────────────────────┘
```

#### 2. Action Buttons (Right Sidebar)
```
For Non-Delivered Orders:
┌─────────────────────────────┐
│ ✓ Mark as Delivered (Demo) │  ← Green button
├─────────────────────────────┤
│ ✗ Cancel Order             │  ← Red button
└─────────────────────────────┘

For Delivered Orders:
┌─────────────────────────────┐
│ 🔄 Return / Exchange       │  ← Blue button
└─────────────────────────────┘
```

#### 3. AuraPoints Earned Card (After Delivery)
```
┌─────────────────────────────┐
│ 💫 AuraPoints Earned!       │
│ ₹75                         │
│ 3% AuraPoints credited      │
│ Valid for 30 days           │
│ [View Wallet]               │
└─────────────────────────────┘
```

### Return Creation Page

#### 1. AuraPoints Warning (Top)
```
┌─────────────────────────────────────────┐
│ ⚠️ Important: AuraPoints Deduction      │
│ If your return is approved, points      │
│ earned from this order will be deducted │
└─────────────────────────────────────────┘
```

#### 2. Return Form
- Issue type selection (cards)
- Description textarea
- Contact information (email/phone)
- Media upload with preview
- Submit button

### Return Details Page

#### 1. Status Badge
- Shows current status with icon
- Color-coded (green=approved, red=rejected, etc.)

#### 2. AI Decision Card
- Decision: APPROVED/REJECTED
- Confidence: 85%
- Reasoning: Detailed explanation

#### 3. Return Information
- Order ID (clickable link back to order)
- Issue type
- Description
- Timestamps
- Contact info

---

## 🔄 Complete User Journey

### Scenario 1: Successful Return (AI Approved)

```
1. User places order (₹2,500)
   ↓
2. User marks as delivered (Demo)
   → AuraPoints: ₹75 (3%) shown
   ↓
3. User clicks "Return / Exchange"
   → Sees warning about point deduction
   ↓
4. User fills return form
   - Issue: Physical damage
   - Description: "Product has scratches"
   - Email: customer@example.com
   - Uploads 2 photos
   ↓
5. AI processes automatically
   → Vision Agent analyzes images
   → Policy Agent checks rules
   → Resolution Agent decides: APPROVED
   → Confidence: 92%
   ↓
6. User sees return details
   → Status: AI_APPROVED
   → Reasoning: "Defect matches manufacturing issue"
   → AuraPoints will be deducted: ₹75
```

### Scenario 2: Manual Review Required

```
1. User places order (₹5,000 - Electronics)
   ↓
2. User marks as delivered
   → AuraPoints: ₹200 (4%) shown
   ↓
3. User clicks "Return / Exchange"
   ↓
4. User fills return form
   - Issue: Functional (not working)
   - Description: "Device won't turn on"
   ↓
5. System routes to manual review
   → Status: MANUAL_REVIEW_PENDING
   → Reason: Functional damage requires inspection
   ↓
6. Admin reviews (future feature)
   → Can approve or reject
   → Adds notes for customer
```

---

## 🧪 Testing Checklist

### Basic Flow
- [ ] Create order
- [ ] View order details
- [ ] See "Mark as Delivered" button
- [ ] Click "Mark as Delivered"
- [ ] Verify status changes to "delivered"
- [ ] Verify AuraPoints card appears
- [ ] Verify "Return / Exchange" button appears
- [ ] Click "Return / Exchange"
- [ ] See AuraPoints warning
- [ ] Fill return form
- [ ] Submit return
- [ ] View return details
- [ ] Verify AI decision shown

### AuraPoints Awareness
- [ ] Info banner visible on order details
- [ ] Points calculation shown after delivery
- [ ] Warning shown on return creation
- [ ] Points deduction mentioned in return details

### Different Order Statuses
- [ ] Pending: No return button
- [ ] Confirmed: No return button, has "Mark as Delivered"
- [ ] Delivered: Has return button
- [ ] Cancelled: No return button

### Different Damage Types
- [ ] Physical damage → AI processing
- [ ] Functional damage → Manual review
- [ ] Cosmetic → AI processing
- [ ] Wrong item → AI processing

---

## 📱 Screenshots Flow

### 1. Order Details (Before Delivery)
```
[Order Summary]
Status: Confirmed
Total: ₹2,500

[Buttons]
✓ Mark as Delivered (Demo)  ← Click this!
✗ Cancel Order
```

### 2. Order Details (After Delivery)
```
[AuraPoints Info Banner]
💫 Earn up to 5% when delivered...

[AuraPoints Earned Card]
💫 AuraPoints Earned!
₹75 (3% credited)

[Buttons]
🔄 Return / Exchange  ← Click this!
```

### 3. Return Creation Form
```
[Warning]
⚠️ AuraPoints will be deducted if approved

[Form]
Issue Type: [Physical Damage]
Description: [Describe problem...]
Email: [your@email.com]
Phone: [+1234567890]
Upload: [Photos...]

[Submit Button]
```

### 4. Return Details
```
[Status Badge]
✓ AI_APPROVED

[AI Decision]
Decision: APPROVED
Confidence: 92%
Reason: Manufacturing defect detected

[Return Info]
Order: ORD-12345
Issue: Physical Damage
Submitted: 2 hours ago
```

---

## 🎯 Key Features Demonstrated

### 1. Demo Functionality
- ✅ "Mark as Delivered" button for testing
- ✅ Instant status change
- ✅ No waiting for actual delivery

### 2. AuraPoints Integration
- ✅ Points calculation shown
- ✅ Warning about deduction
- ✅ Clear communication throughout

### 3. Return Flow
- ✅ Easy access from order details
- ✅ Simple form with validation
- ✅ AI processing with instant feedback
- ✅ Clear status tracking

### 4. User Awareness
- ✅ Info banners
- ✅ Warning messages
- ✅ Confirmation dialogs
- ✅ Clear next steps

---

## 🚀 Quick Start Commands

```bash
# Start Backend
cd backend
uvicorn app.main:app --reload

# Start Frontend
cd frontend
npm run dev

# Open in Browser
http://localhost:3000
```

---

## 💡 Pro Tips

1. **Quick Demo Path:**
   - Create order → Mark delivered → Return immediately

2. **Test AI Analysis:**
   - Upload clear images of defects
   - Describe issue in detail
   - AI gives better decisions with more info

3. **Check AuraPoints:**
   - Always visible on order details
   - Wallet page shows total balance
   - Return page warns about deduction

4. **Multiple Returns:**
   - Can create return for any delivered order
   - Each return tracked independently
   - Status updates in real-time

---

## ✅ Success Indicators

You'll know it's working when:
1. ✅ "Mark as Delivered" button appears on non-delivered orders
2. ✅ After clicking, status changes and points show
3. ✅ "Return / Exchange" button appears
4. ✅ Return form loads with order info
5. ✅ Submission creates return request
6. ✅ AI decision appears within seconds
7. ✅ All info banners and warnings visible

---

**Demo Ready!** 🎉

The return system is fully integrated with AuraPoints awareness and a convenient demo button for testing.
