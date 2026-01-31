# AuraShop – AI-Powered Personalized Shopping Assistant

A full-stack, hackathon-ready prototype that delivers **real-time AI product recommendations** based on user behavior, preferences, browsing history, and intent. Built for e-commerce and omnichannel environments.

**Quick start:** Run the **backend first** (port 8000), then the frontend. If the backend is not running, the frontend still loads with fallback product data and shows a banner with the start command.

## ✨ Features

- **🔍 Smart Search** – Real-time product search across name, description, category, tags, and brand with dedicated search page.
- **🏪 In-Store Pickup with QR Code** – Customers can choose store pickup, receive unique QR code, and scan at store for instant verification and pickup.
- **👤 Profile & Order Management** – User profiles with order history, contact info, saved addresses, and order tracking.
- **📦 Order Tracking** – Real-time order status updates (Pending → Confirmed → Ready for Pickup/Out for Delivery → Picked Up/Delivered).
- **💰 Aura Wallet** – AuraPoints rewards system: earn 5-7% on every purchase, valid for 30 days, automatic credit after order completion.
- **🤖 Intelligent AI Assistant** – Enhanced chatbot with deep product knowledge, personalization, comparison capabilities, and contextual recommendations. Understands complex queries like "best phone under 30k" or "formal wear for interview".
- **✨ Beautiful Modern UI** – Stunning gradient hero with Unsplash backgrounds, glass-morphism effects, smooth animations, and premium design throughout.
- **🖼️ Unsplash Integration** – High-quality, category-specific images for all products and dynamic hero backgrounds.
- **🎯 AI Recommendation Engine** – Ranks products using user preferences, session behavior, cart contents, and budget signals (OpenAI + rule-based fallback).
- **💬 Enhanced Chat Experience** – Natural language queries, product suggestions, budget-aware alternatives, inline product cards, 6 suggested prompts, emoji support, and gradient UI.
- **📊 Session-based Tracking** – Page views, product clicks, search queries, cart add/remove, time spent, budget signals, category affinity.
- **🎨 Personalized UI** – "Recommended for You" and "Trending" carousels, AI badges (Best Match, Value for Money, Trending), top picks on product listing, "Why this product is right for you" and similar products on detail, upsell/cross-sell on cart.
- **📱 Fully Responsive** – Desktop and mobile optimized with Tailwind CSS, modern components, and smooth transitions.
- **🔄 Graceful Degradation** – Works offline with fallback product data when backend is down, shows helpful banner with start instructions.

## Tech Stack

| Layer        | Stack                          |
|-------------|---------------------------------|
| Frontend    | Next.js 14, React, Tailwind, ShadCN-style UI, Framer Motion, Unsplash |
| Backend     | Python, FastAPI                 |
| AI          | OpenAI API (gpt-4o-mini), prompt-engineered recommendations & chat |
| Data        | In-memory store, synthetic product catalog (JSON) |

## Project Structure

```
AuraShop/
├── backend/                 # FastAPI app
│   ├── app/
│   │   ├── main.py          # REST + events + recommendations + chat
│   │   ├── models.py        # Pydantic models
│   │   ├── data_store.py    # In-memory sessions, events, cart, cache
│   │   ├── ai_service.py    # Enhanced AI: recommendations + smart chat
│   │   └── config.py        # Env (OPENAI_API_KEY, CORS)
│   └── data/
│       └── products.json    # Synthetic catalog
├── frontend/                # Next.js app
│   └── src/
│       ├── app/             # Pages: home, products, product/[id], cart, search
│       ├── components/      # Header with search, ProductCard with Unsplash, 
│       │                    # ProductCarousel, ChatWidget (enhanced), BackendOfflineBanner
│       └── lib/             # api.ts (with fallbacks), session.ts, utils, unsplash.ts
└── README.md
```

## Setup

**Run the backend first.** The frontend proxies `/api/*` to `http://localhost:8000`. If nothing is listening on port 8000, you'll see connection errors until the backend is started. The frontend will still show products using fallback data and a "Backend not running" banner.

### 1. Backend (Python) — start this first

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
# requirements.txt includes chromadb + numpy for RAG (semantic product search + FAQ). Optional: works without them using keyword-only recommend and fallback FAQ.
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
# Edit .env and set: OPENAI_API_KEY=sk-your-openai-key
```

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API base: `http://localhost:8000`. Docs: `http://localhost:8000/docs`.

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

App: `http://localhost:3000`. The app uses Next.js rewrites so `/api/*` is proxied to `http://localhost:8000/*`.

### 3. Environment

**Backend** (`backend/.env`):

- `OPENAI_API_KEY` – Your OpenAI API key (used for intent classification and FAQ LLM in recommend.chatbot).
- `CORS_ORIGINS` – Default `http://localhost:3000`.
- **RAG (default):** Recommendations and chat use the recommend module (Chroma + semantic search, recommend.chatbot). Set `USE_FAST_RECOMMEND=1` and/or `USE_FAST_CHAT=1` to use only JSON products and a static chat reply (no Chroma load) if you want instant startup.

No env vars are required in the frontend for the default setup.

### 4. How everything is connected

- **Frontend (Next.js)** → calls backend at `http://localhost:8000` via `/api/*` proxy (products, recommendations, chat, cart, orders, wallet).
- **Backend (FastAPI)** → serves API; uses **JSON files** for primary persistence (`data/products.json`, `data/orders.json`) and **recommend DB** (SQLite `data/recommend.db` or MySQL via `MYSQL_URI`) for RAG.
- **Database (recommend)** → On startup the backend ensures the recommend DB has tables and syncs **products**, **orders**, and **FAQ** from JSON into the DB so RAG, habits, and the recommendation engine see the same data. Every new order is written to both `orders.json` and the recommend DB.
- **RAG (Chroma + recommend)** → Reads products, orders, and FAQ from the recommend DB for semantic search and chatbot. Run `python -m scripts.build_rag_index` after first sync to build Chroma indices.

So: **Frontend → Backend API → JSON + recommend DB**; RAG uses the same DB.

## API Overview

| Method | Endpoint              | Description                    |
|--------|------------------------|--------------------------------|
| GET    | `/products`            | List products (filters: category, price, rating, color) |
| GET    | `/products/{id}`       | Product detail                 |
| POST   | `/events`              | Track behavior (page_view, product_click, search, cart_add, cart_remove, etc.) |
| POST   | `/recommendations`     | Get AI recommendations (query: session_id, limit, max_price, category, exclude_product_ids) |
| POST   | `/chat`                | Enhanced AI chat (body: session_id, message, history) |
| GET    | `/session/{id}/cart`   | Get cart for session           |
| GET    | `/stores`              | Get available stores for pickup |
| POST   | `/orders`              | Create order (home delivery or store pickup) |
| GET    | `/orders/{id}`         | Get order details with QR code |
| GET    | `/users/{id}/orders`   | Get all orders for user        |
| POST   | `/pickup/verify`       | Verify QR code for store pickup |
| POST   | `/pickup/complete/{id}`| Mark order as picked up        |
| GET    | `/users/{id}/profile`  | Get user profile               |
| POST   | `/users/{id}/profile`  | Create/update user profile     |
| GET    | `/users/{id}/wallet`   | Get Aura Wallet details        |
| GET    | `/users/{id}/wallet/transactions` | Get wallet transaction history |
| GET    | `/wallet/preview-cashback` | Preview cashback for order total |

## 🎨 Demo Flow

1. **Home** – Open `http://localhost:3000`. See stunning hero with Unsplash background, gradient overlays, animated badges, "✨ Recommended for You" and "🔥 Trending Now" carousels with AI badges.

2. **Search** – Use the search bar in header (desktop) or below logo (mobile). Try: "shirt", "electronics", "casual", "formal". See instant filtered results with Unsplash images.

3. **Smart AI Chat** – Click the gradient floating chat button (bottom-right, with green pulse indicator). Try complex queries:
   - "Find me something under ₹2000"
   - "Best casual wear for office"
   - "Compare top-rated electronics"
   - "Gift ideas for tech lover"
   - "Outfit for party under ₹5000"
   - "Show trending products"
   
   See inline product cards, personalized reasoning with emojis (✨, 🎯, 💡), and 6 suggested prompts.

4. **Products** – Go to Products page. Use smart filters (category, price range, rating). See "Top picks based on your browsing" banner if you have session history. All products show high-quality Unsplash images.

5. **Product Detail** – Click any product. See large Unsplash image with hover zoom, "Why this product is right for you" section with personalized insights, and "Similar & alternatives" recommendations.

6. **Cart** – Add items (cart badge pulses), go to Cart. See order summary, "People like you also bought" upsells with Unsplash images. Remove items and see real-time cart update.

7. **Checkout** – Click "Proceed to checkout". Choose between:
   - **Home Delivery**: Enter address, place order
   - **Store Pickup**: Select store location, place order, receive QR code

8. **Order Detail** – After placing order, see:
   - Order status with icon badges
   - QR code (for store pickup) - large, scannable, with alphanumeric code
   - Order items and total
   - Delivery/pickup information

9. **Profile & Orders** – Click profile icon in header:
   - View/edit personal information
   - See all orders with status badges
   - Click any order to view details and QR code
   - Quick stats (total orders, completed)

10. **Store Scanner** (Staff Only) – Visit `/store-scanner`:
    - Enter/scan QR code
    - Verify order details
    - Complete pickup with one click
    - See confirmation animation

## Success Metrics (for judging)

- **Reduced search time** – Smart search + AI chat surface relevant products in seconds.
- **Higher click-through** – Stunning Unsplash images, AI badges, and "top picks" drive engagement.
- **Better recommendations** – Enhanced AI understands complex queries and user context.
- **Cart completion** – Personalized upsells, low-stock nudges, and smooth UX increase conversions.
- **Explainability** – "Why this product is right for you" and recommendation reasons build trust.
- **Visual appeal** – Modern gradient design, glass effects, and professional imagery create premium feel.

## 🚀 New Features Added

### Search Functionality
- Header search bar (responsive: desktop + mobile)
- Dedicated `/search` page with real-time filtering
- Searches across: name, description, category, tags, brand
- Empty state with helpful message

### Enhanced AI Chatbot
- **Smarter prompts**: Deep product knowledge, comparison capabilities, complex query understanding
- **Better personality**: Warm, knowledgeable, uses emojis sparingly (✨, 🎯, 💡)
- **6 suggested prompts**: Including "Gift ideas", "Compare products", "Outfit suggestions"
- **Enhanced UI**: Gradient header, online indicator with pulse, larger chat window
- **Contextual responses**: References browsing history, cart items, budget constraints

### Beautiful UI Improvements
- **Gradient hero**: Stunning purple gradient overlay on Unsplash background
- **Glass-morphism**: Backdrop blur effects on badges and chat
- **Unsplash images**: Category-specific high-quality images for all products
- **Smooth animations**: Framer Motion for hero, products, and interactions
- **Enhanced header**: Gradient logo, search integration, pulsing cart badge
- **Better colors**: Refined color palette with subtle background gradients
- **Premium feel**: Shadow effects, rounded corners, smooth transitions

## 📚 Additional Documentation

- **`ENHANCEMENTS.md`** - Detailed breakdown of search, AI improvements, and UI enhancements
- **`NEW_FEATURES.md`** - Complete guide to store pickup, profile, and order management
- **`STORE_PICKUP_GUIDE.md`** - Technical documentation for QR pickup system
- **`DEMO_GUIDE.md`** - Step-by-step presentation guide for hackathon judges

## 🎯 Hackathon Readiness

This project is **100% demo-ready** with:
- ✅ Complete feature set (browse, search, chat, cart, checkout, orders, profile)
- ✅ Innovative QR pickup system
- ✅ Beautiful, modern UI with Unsplash images
- ✅ Smart AI assistant with OpenAI
- ✅ Responsive design (mobile + desktop)
- ✅ Error handling and fallbacks
- ✅ Comprehensive documentation
- ✅ Clear demo flow and talking points

## Troubleshooting

### `ECONNRESET` / "Failed to proxy http://localhost:8000/..."

The frontend proxies `/api/*` to the backend. This error means **the backend is not running** or the connection was reset.

**Fix:** Start the backend first in a separate terminal:

```bash
cd backend
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Keep this running, then use the frontend at `http://localhost:3000`. The app will show a "Backend not running" banner until the backend is up.

### "upstream image response failed" (503)

Product and hero images use **Picsum Photos** (no API key, reliable). If you see 503 from an image URL, it’s usually temporary; refresh the page. Unsplash Source was deprecated and is no longer used.

## License

MIT.

