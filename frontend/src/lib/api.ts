const API = "/api";

function isNetworkError(e: unknown): boolean {
  const msg = e instanceof Error ? e.message : String(e);
  if (e instanceof TypeError && /fetch|network/i.test(msg)) return true;
  return /ECONNREFUSED|Failed to fetch|NetworkError/i.test(msg);
}

export type Product = {
  id: string;
  name: string;
  description: string;
  price: number;
  currency: string;
  category: string;
  subcategory?: string;
  brand?: string;
  rating: number;
  review_count: number;
  colors: string[];
  sizes: string[];
  image_url?: string;
  tags: string[];
  in_stock: boolean;
  stock_count?: number;
};

export type EventType =
  | "page_view"
  | "product_click"
  | "search"
  | "cart_add"
  | "cart_remove"
  | "time_spent"
  | "budget_signal"
  | "category_view";

export type EventPayload = {
  event_type: EventType;
  session_id: string;
  user_id?: string;
  product_id?: string;
  category?: string;
  query?: string;
  amount?: number;
  duration_seconds?: number;
  metadata?: Record<string, unknown>;
};

export type RecommendationItem = {
  product_id: string;
  reason: string;
  confidence: number;
  product?: Partial<Product>;
};

/** Engine rec types: category | search_no_buy | already_bought | out_of_stock_notify | festival | habits */
export type EngineRecType =
  | "category"
  | "search_no_buy"
  | "already_bought"
  | "out_of_stock_notify"
  | "festival"
  | "habits";

/** Ensure a numeric value is finite; avoid NaN being passed to React children. */
function safeNum(value: unknown, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

/** Normalize engine rec item (id or product_id, optional fields) to Product. */
function engineRecToProduct(rec: Record<string, unknown>): Product {
  const id = (rec.id ?? rec.product_id ?? "") as string;
  return {
    id,
    name: (rec.name as string) ?? "",
    description: (rec.description as string) ?? "",
    price: safeNum(rec.price, 0),
    currency: (rec.currency as string) ?? "INR",
    category: (rec.category as string) ?? "",
    rating: safeNum(rec.rating, 0),
    review_count: safeNum(rec.review_count, 0),
    colors: Array.isArray(rec.colors) ? (rec.colors as string[]) : [],
    sizes: Array.isArray(rec.sizes) ? (rec.sizes as string[]) : [],
    tags: Array.isArray(rec.tags) ? (rec.tags as string[]) : [],
    in_stock: rec.in_stock !== false,
    image_url: rec.image_url as string | undefined,
    stock_count: rec.stock_count != null && Number.isFinite(Number(rec.stock_count)) ? Number(rec.stock_count) : undefined,
  };
}

export async function fetchRecommendationsByEngine(
  actorId: string,
  type: EngineRecType,
  limit: number = 10
): Promise<{ recommendations: Product[] }> {
  try {
    const search = new URLSearchParams({ user_id: actorId, type, limit: String(limit) });
    const res = await fetch(`${API}/recommendations/engine?${search}`);
    if (!res.ok) throw new Error("Failed to fetch engine recommendations");
    const data = (await res.json()) as { recommendations?: Record<string, unknown>[] };
    const raw = data.recommendations ?? [];
    const products = raw
      .map((r) => engineRecToProduct(r))
      .filter((p) => p.id && p.name);
    return { recommendations: products };
  } catch (e) {
    if (isNetworkError(e)) return { recommendations: [] };
    throw e;
  }
}

export async function fetchCategories(): Promise<{ categories: string[] }> {
  try {
    const res = await fetch(`${API}/categories`);
    if (!res.ok) return { categories: [] };
    return res.json();
  } catch (e) {
    if (isNetworkError(e)) return { categories: ["Clothing", "Electronics", "Accessories", "Footwear"] };
    throw e;
  }
}

export async function fetchProducts(params?: {
  category?: string;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  color?: string;
  limit?: number;
}): Promise<{ products: Product[] }> {
  try {
    const search = new URLSearchParams();
    if (params?.category) search.set("category", params.category);
    if (params?.min_price != null) search.set("min_price", String(params.min_price));
    if (params?.max_price != null) search.set("max_price", String(params.max_price));
    if (params?.min_rating != null) search.set("min_rating", String(params.min_rating));
    if (params?.color) search.set("color", params.color);
    if (params?.limit) search.set("limit", String(params.limit));
    const res = await fetch(`${API}/products?${search}`);
    if (!res.ok) throw new Error("Failed to fetch products");
    return res.json();
  } catch (e) {
    if (isNetworkError(e) || (e instanceof Error && e.message === "Failed to fetch products")) {
      const { getFallbackProducts } = await import("./fallback-products");
      return { products: getFallbackProducts(params) };
    }
    throw e;
  }
}

export async function fetchProduct(id: string): Promise<Product> {
  try {
    const res = await fetch(`${API}/products/${id}`);
    if (!res.ok) throw new Error("Product not found");
    return res.json();
  } catch (e) {
    if (isNetworkError(e)) {
      const { getFallbackProduct } = await import("./fallback-products");
      const p = getFallbackProduct(id);
      if (p) return p;
    }
    throw e;
  }
}

export async function trackEvent(payload: EventPayload): Promise<void> {
  try {
    await fetch(`${API}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    if (isNetworkError(e)) return; // no-op when backend is down
    throw e;
  }
}

export async function fetchRecommendations(
  sessionId: string,
  opts?: { limit?: number; max_price?: number; category?: string; exclude_product_ids?: string; user_id?: string }
): Promise<{ recommendations: RecommendationItem[] }> {
  try {
    const search = new URLSearchParams({ session_id: sessionId });
    if (opts?.user_id) search.set("user_id", opts.user_id);
    if (opts?.limit) search.set("limit", String(opts.limit));
    if (opts?.max_price != null) search.set("max_price", String(opts.max_price));
    if (opts?.category) search.set("category", opts.category);
    if (opts?.exclude_product_ids) search.set("exclude_product_ids", opts.exclude_product_ids);
    const res = await fetch(`${API}/recommendations?${search}`);
    if (!res.ok) throw new Error("Failed to fetch recommendations");
    return res.json();
  } catch (e) {
    if (isNetworkError(e)) {
      const { getFallbackProducts } = await import("./fallback-products");
      const limit = opts?.limit ?? 5;
      const products = getFallbackProducts({ limit, category: opts?.category, max_price: opts?.max_price });
      return {
        recommendations: products.map((p) => ({
          product_id: p.id,
          reason: "Recommended for you",
          confidence: 0.8,
          product: p,
        })),
      };
    }
    throw e;
  }
}

export async function chat(
  sessionId: string,
  message: string,
  history?: { role: string; content: string }[],
  user_id?: string
): Promise<{ content: string; product_ids: string[] }> {
  try {
    const body: { session_id: string; message: string; history?: { role: string; content: string }[]; user_id?: string } = { session_id: sessionId, message, history };
    if (user_id) body.user_id = user_id;
    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Chat failed");
    return res.json();
  } catch (e) {
    if (isNetworkError(e) || (e instanceof Error && e.message === "Chat failed")) {
      return {
        content: "The backend API isn’t running or had an error. Start it with: cd backend && uvicorn app.main:app --reload --port 8000",
        product_ids: [],
      };
    }
    throw e;
  }
}

export type ChatStreamCallbacks = {
  onChunk: (content: string) => void;
  onDone: (productIds: string[]) => void;
  onError?: (err: Error) => void;
};

/** Stream chat response (SSE) for a generative-AI feel. Calls onChunk for each token, onDone with product_ids. */
export async function chatStream(
  sessionId: string,
  message: string,
  history: { role: string; content: string }[] | undefined,
  callbacks: ChatStreamCallbacks,
  user_id?: string
): Promise<void> {
  try {
    const body: { session_id: string; message: string; history: { role: string; content: string }[]; user_id?: string } = { session_id: sessionId, message, history: history ?? [] };
    if (user_id) body.user_id = user_id;
    const res = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok || !res.body) {
      callbacks.onDone([]);
      if (res.status >= 400) callbacks.onError?.(new Error("Chat stream failed"));
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    const productIds: string[] = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6)) as { content?: string; done?: boolean; product_ids?: string[] };
            if (data.content != null) callbacks.onChunk(data.content);
            if (data.done === true && Array.isArray(data.product_ids)) {
              productIds.push(...data.product_ids);
              callbacks.onDone(productIds);
              return;
            }
          } catch {
            // skip malformed line
          }
        }
      }
    }
    callbacks.onDone(productIds);
  } catch (e) {
    callbacks.onError?.(e instanceof Error ? e : new Error(String(e)));
    callbacks.onDone([]);
  }
}

export type CartItem = Product & { quantity: number };

export async function getCart(sessionId: string, userId?: string): Promise<{ cart: CartItem[] }> {
  try {
    const url = userId ? `${API}/session/${sessionId}/cart?user_id=${encodeURIComponent(userId)}` : `${API}/session/${sessionId}/cart`;
    const res = await fetch(url);
    if (!res.ok) return { cart: [] };
    return res.json();
  } catch (e) {
    if (isNetworkError(e)) return { cart: [] };
    throw e;
  }
}

/** Set quantity for a product in cart. quantity 0 removes. Returns updated cart. */
export async function updateCartQuantity(
  sessionId: string,
  productId: string,
  quantity: number,
  userId?: string
): Promise<{ cart: CartItem[] }> {
  const url = userId
    ? `${API}/session/${sessionId}/cart/item?user_id=${encodeURIComponent(userId)}`
    : `${API}/session/${sessionId}/cart/item`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, quantity }),
  });
  if (!res.ok) throw new Error("Failed to update cart");
  return res.json();
}

export async function addToCart(sessionId: string, productId: string, userId?: string): Promise<void> {
  await trackEvent({
    event_type: "cart_add",
    session_id: sessionId,
    product_id: productId,
    ...(userId ? { user_id: userId } : {}),
  });
}

/** Send OTP to email – OTP is printed in the backend terminal. */
export async function sendOtp(email: string): Promise<{ success: boolean; message?: string }> {
  const res = await fetch(`${API}/auth/send-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase() }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Failed to send OTP");
  return data;
}

/** Verify OTP and get user info for login. */
export async function verifyOtp(
  email: string,
  otp: string
): Promise<{ success: boolean; user_id: string; email: string; name: string }> {
  const res = await fetch(`${API}/auth/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim().toLowerCase(), otp: otp.trim() }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Invalid or expired OTP");
  return data;
}

export async function mergeCart(sessionId: string, userId: string): Promise<{ success: boolean }> {
  const res = await fetch(`${API}/auth/merge-cart?session_id=${encodeURIComponent(sessionId)}&user_id=${encodeURIComponent(userId)}`, {
    method: "POST",
  });
  if (!res.ok) return { success: false };
  return res.json().catch(() => ({ success: false }));
}

export async function removeFromCart(sessionId: string, productId: string): Promise<void> {
  await trackEvent({
    event_type: "cart_remove",
    session_id: sessionId,
    product_id: productId,
  });
}

export type Order = {
  id: string;
  user_id: string;
  items: Array<{ product_id: string; quantity: number; price: number }>;
  total: number;
  delivery_method: string;
  status: string;
  created_at: string;
};

export async function fetchUserOrders(userId: string): Promise<{ orders: Order[] }> {
  try {
    const res = await fetch(`${API}/users/${userId}/orders`);
    if (!res.ok) return { orders: [] };
    return res.json();
  } catch (e) {
    if (isNetworkError(e)) return { orders: [] };
    throw e;
  }
}

export type CouponGameResult = {
  played: boolean;
  won: boolean;
  code: string | null;
  min_order: number;
  discount: number;
  message: string;
};

export async function playCouponGame(sessionId: string): Promise<CouponGameResult> {
  const res = await fetch(`${API}/home/coupon-game`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Failed to play");
  return res.json();
}

export async function playJackpot(sessionId: string): Promise<CouponGameResult> {
  const res = await fetch(`${API}/home/jackpot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Failed to play");
  return res.json();
}

export async function playScratch(sessionId: string): Promise<CouponGameResult> {
  const res = await fetch(`${API}/home/scratch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Failed to play");
  return res.json();
}
