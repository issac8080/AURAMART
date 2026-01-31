# Return & Exchange Module - Quick Start Guide

## 🎯 Overview
The return & exchange module has been **successfully integrated** into AuraShop with **zero authentication** requirements. It works autonomously using Order ID and customer contact information.

---

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
Create/update `backend/.env`:
```bash
OPENAI_API_KEY=your_openai_api_key_here
CORS_ORIGINS=http://localhost:3000

# Optional: For AI tracing
OPIK_API_KEY=your_opik_key
OPIK_WORKSPACE=your_workspace
OPIK_PROJECT_NAME=AuraShop-Returns
```

### 3. Start Services
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

---

## 📱 User Flow

### Step 1: View Order
Navigate to: `http://localhost:3000/orders/{orderId}`

### Step 2: Click "Return / Exchange"
- Button appears for orders with status: `delivered` or `picked_up`
- No login required!

### Step 3: Fill Return Form
- **Select Issue Type**: Physical, Functional, Cosmetic, etc.
- **Describe Problem**: Minimum 10 characters
- **Contact Info**: Provide email OR phone (at least one)
- **Upload Media**: Optional photos/videos (max 5MB each)

### Step 4: Submit
- AI processes automatically
- Instant decision or manual review
- Redirects to return details page

### Step 5: Track Status
View at: `http://localhost:3000/returns/{returnId}`
- See AI decision and confidence
- View reasoning
- Check admin notes (if manually reviewed)

---

## 🔧 API Endpoints

### Create Return Request
```bash
POST http://localhost:8000/api/returns/
Content-Type: application/json

{
  "order_id": "ORD-12345",
  "damage_type": "PHYSICAL",
  "description": "Product has scratches on the surface",
  "category": "Electronics",
  "customer_email": "customer@example.com",
  "customer_phone": "+1234567890",
  "media_base64": [
    {
      "data": "base64_encoded_image_data",
      "mime_type": "image/jpeg",
      "filename": "damage.jpg"
    }
  ]
}
```

### Get Return by ID
```bash
GET http://localhost:8000/api/returns/{return_id}
```

### Get Return by Order ID
```bash
GET http://localhost:8000/api/returns/order/{order_id}
```

### List All Returns
```bash
GET http://localhost:8000/api/returns/
GET http://localhost:8000/api/returns/?order_id=ORD-12345
GET http://localhost:8000/api/returns/?status=AI_APPROVED
```

---

## 🤖 AI Pipeline

### 1. Vision Agent
- Analyzes uploaded images using GPT-4o Vision
- Detects defects, severity, location
- Determines probable cause (manufacturing vs user damage)
- Outputs confidence score

### 2. Policy Agent
- Retrieves relevant policies using RAG (ChromaDB)
- Matches issue against return policies
- Interprets policy applicability
- Recommends approve/reject

### 3. Resolution Agent
- Makes final decision: APPROVED / REJECTED / ESCALATE
- Considers vision analysis + policy match + confidence
- Low confidence → escalates to manual review

### 4. Communication Agent
- Generates user-friendly messages
- Explains decision reasoning
- Provides next steps

---

## 📊 Status Flow

```
PENDING
   ↓
MANUAL_REVIEW_PENDING (if functional damage or low confidence)
   ↓
AI_APPROVED / AI_REJECTED (if AI processed)
   ↓
ADMIN_APPROVED / ADMIN_REJECTED (if manually reviewed)
   ↓
PROCESSING
   ↓
COMPLETED
```

---

## 🎨 UI Components

### Pages Created:
1. **`/returns/create`** - Return request form
2. **`/returns/[id]`** - Return status details

### Modified:
- **`/orders/[id]`** - Added "Return / Exchange" button

### Design System:
- Uses AuraShop's existing components
- Matches color palette and typography
- Responsive and accessible
- No custom styling needed

---

## ✅ What's Removed (Authentication)

### Backend:
- ❌ `/api/auth/login` endpoint
- ❌ User session management
- ❌ JWT token validation
- ❌ `get_current_user` dependency
- ❌ Protected route decorators

### Frontend:
- ❌ Login page
- ❌ `ProtectedRoute` components
- ❌ User session storage
- ❌ Authentication checks

### Replaced With:
- ✅ Order ID validation
- ✅ Customer email/phone for updates
- ✅ Open API endpoints

---

## 🧪 Testing

### Test Return Creation:
```bash
# 1. Create a test order (if needed)
curl -X POST "http://localhost:8000/api/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "user_id": "test-user",
    "items": [{"product_id": "1", "quantity": 1, "price": 1000}],
    "delivery_method": "home_delivery",
    "delivery_address": "123 Test St"
  }'

# 2. Update order status to delivered
curl -X POST "http://localhost:8000/api/orders/{order_id}/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "delivered"}'

# 3. Create return request
curl -X POST "http://localhost:8000/api/returns/" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "{order_id}",
    "damage_type": "PHYSICAL",
    "description": "Product has scratches and dents",
    "category": "Electronics",
    "customer_email": "test@example.com",
    "media_base64": []
  }'

# 4. View return details
curl "http://localhost:8000/api/returns/{return_id}"
```

---

## 🐛 Troubleshooting

### Return module not loading?
Check backend logs for:
```
✓ Return & Exchange module loaded successfully
```

If you see an error, ensure:
1. All dependencies installed: `pip install -r requirements.txt`
2. `backend/app/returns/` directory exists
3. No import errors in services

### AI not working?
1. Check `OPENAI_API_KEY` in `.env`
2. Verify OpenAI API key is valid
3. Check backend logs for AI agent errors

### Images not uploading?
1. Check file size (max 5MB)
2. Verify base64 encoding
3. Check MIME type is supported

---

## 📚 File Structure

```
backend/
  app/
    returns/
      __init__.py
      models.py              # Pydantic models
      db_models.py           # SQLAlchemy models
      schemas.py             # Request/response schemas
      routes.py              # API endpoints (no auth)
      db.py                  # Database config
      config.py              # Module config
      services/
        returns_service.py   # Main orchestration
        vision_agent.py      # Image analysis
        policy_agent.py      # Policy matching
        resolution_agent.py  # Decision making
        communication_agent.py # User messaging
        returns_workflow.py  # LangGraph workflow
        admin_service.py     # Manual review

frontend/
  src/
    app/
      returns/
        create/
          page.tsx           # Return request form
        [id]/
          page.tsx           # Return details
      orders/
        [id]/
          page.tsx           # Modified: Added return button
```

---

## 🎉 Success!

The return & exchange module is now fully integrated and working autonomously. No authentication required, UI matches AuraShop perfectly, and all business logic is preserved.

**Ready to use!** 🚀
