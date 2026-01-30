const API = "/api";

export type CartItemForDiscount = {
  product_id: string;
  price: number;
  quantity: number;
  brand?: string;
};

export async function fetchApplicableDiscounts(
  userId: string,
  sessionId: string,
  orderTotal: number,
  cartItems: CartItemForDiscount[] = []
): Promise<{ discounts: import("./types").AppliedDiscount[] }> {
  const search = new URLSearchParams({
    user_id: userId,
    session_id: sessionId,
    order_total: String(orderTotal),
    cart_items: JSON.stringify(cartItems),
  });
  const res = await fetch(`${API}/discounts/applicable?${search}`);
  if (!res.ok) throw new Error("Failed to fetch discounts");
  return res.json();
}

export async function fetchPriceDropNotifications(
  sessionId: string,
  userId?: string
): Promise<{ notifications: import("./types").PriceDropNotification[] }> {
  const search = new URLSearchParams({ session_id: sessionId });
  if (userId) search.set("user_id", userId);
  const res = await fetch(`${API}/discounts/price-drop-notifications?${search}`);
  if (!res.ok) return { notifications: [] };
  return res.json();
}

export async function recordProductView(
  sessionId: string,
  productId: string,
  userId?: string
): Promise<void> {
  const search = new URLSearchParams({ session_id: sessionId, product_id: productId });
  if (userId) search.set("user_id", userId);
  await fetch(`${API}/discounts/record-view?${search}`, { method: "POST" });
}

export async function fetchSubscriptionTiers(): Promise<{
  tiers: import("./types").SubscriptionTier[];
}> {
  const res = await fetch(`${API}/discounts/subscription-tiers`);
  if (!res.ok) return { tiers: [] };
  return res.json();
}

export async function fetchFestivals(): Promise<{
  festivals: import("./types").Festival[];
}> {
  const res = await fetch(`${API}/discounts/festivals`);
  if (!res.ok) return { festivals: [] };
  return res.json();
}

export async function setUserSubscription(
  userId: string,
  tierId: string | null
): Promise<void> {
  const search = new URLSearchParams({ user_id: userId });
  if (tierId) search.set("tier_id", tierId);
  await fetch(`${API}/discounts/subscription?${search}`, { method: "POST" });
}

export async function simulatePriceDrop(
  productId: string,
  newPrice: number
): Promise<void> {
  const search = new URLSearchParams({
    product_id: productId,
    new_price: String(newPrice),
  });
  const res = await fetch(`${API}/discounts/simulate-price-drop?${search}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to simulate price drop");
}
