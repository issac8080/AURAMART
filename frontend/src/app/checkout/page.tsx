"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Script from "next/script";
import { motion } from "framer-motion";
import { ShoppingBag, Home, Store, Check, ArrowLeft, Tag, Sparkles, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCart, useAuth } from "@/app/providers";
import { getCart } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import Link from "next/link";
import { fetchApplicableDiscounts } from "@/discountFrontend/api";
import { DiscountCard } from "@/discountFrontend/DiscountCard";
import type { AppliedDiscount } from "@/discountFrontend/types";

const API = "/api";

const AUTH_HEADERS = () => ({ "X-Logged-In": "true", "Content-Type": "application/json" });

/** Indian phone: 10 digits, optional +91 prefix */
function isValidPhone(v: string): boolean {
  const digits = v.replace(/\D/g, "");
  return digits.length === 10 || (digits.length === 12 && digits.startsWith("91"));
}

declare global {
  interface Window {
    Razorpay: new (options: {
      key: string;
      amount: number;
      order_id: string;
      name?: string;
      description?: string;
      handler: (response: { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string }) => void;
    }) => { open: () => void };
  }
}

type Store = {
  id: string;
  name: string;
  address: string;
};

export default function CheckoutPage() {
  const router = useRouter();
  const { sessionId } = useCart();
  const { user } = useAuth();
  const userId = user?.user_id ?? sessionId;
  const [cart, setCart] = useState<any[]>([]);
  const [deliveryMethod, setDeliveryMethod] = useState<"home_delivery" | "store_pickup">("home_delivery");
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStore, setSelectedStore] = useState("");
  const [address, setAddress] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [cashbackPreview, setCashbackPreview] = useState<{ amount: number; rate: string } | null>(null);
  const [discounts, setDiscounts] = useState<AppliedDiscount[]>([]);
  const [errors, setErrors] = useState<{ name?: string; phone?: string; address?: string; store?: string }>({});

  const total = cart.reduce((sum, p) => sum + p.price * (p.quantity ?? 1), 0);
  const cartItemsForDiscount = cart.map((p) => ({
    product_id: p.id,
    price: p.price,
    quantity: p.quantity ?? 1,
    brand: p.brand,
  }));
  const totalDiscountAmount = discounts.reduce((sum, d) => sum + d.amount, 0);
  const totalAfterDiscount = Math.max(0, total - totalDiscountAmount);

  useEffect(() => {
    if (!user) {
      router.replace("/login?next=/checkout");
      return;
    }
  }, [user, router]);

  useEffect(() => {
    async function loadCart() {
      try {
        const { cart: cartData } = await getCart(sessionId, user?.user_id);
        setCart(cartData || []);
      } catch {}
    }
    async function loadStores() {
      try {
        const res = await fetch(`${API}/stores`);
        const data = await res.json();
        setStores(data.stores || []);
        if (data.stores?.length) setSelectedStore(data.stores[0].id);
      } catch {}
    }
    if (sessionId) {
      loadCart();
      loadStores();
    }
  }, [sessionId, user?.user_id]);

  useEffect(() => {
    async function previewCashback() {
      if (total > 0) {
        try {
          const res = await fetch(`${API}/wallet/preview-cashback?order_total=${total}`);
          if (res.ok) {
            const data = await res.json();
            setCashbackPreview({
              amount: data.points_amount || data.cashback_amount,
              rate: data.points_rate || data.cashback_rate,
            });
          }
        } catch {}
      }
    }
    previewCashback();
  }, [total]);

  useEffect(() => {
    if (!sessionId || total <= 0) return;
    const items = cart.map((p) => ({
      product_id: p.id,
      price: p.price,
      quantity: p.quantity ?? 1,
      brand: p.brand,
    }));
    fetchApplicableDiscounts(sessionId, sessionId, total, items)
      .then((data) => setDiscounts(data.discounts || []))
      .catch(() => setDiscounts([]));
  }, [sessionId, total, cart.length, cart.map((p) => p.id).join(",")]);

  const validate = useCallback((): boolean => {
    const next: typeof errors = {};
    const nameTrim = (name || "").trim();
    if (nameTrim.length < 2) next.name = "Name must be at least 2 characters";
    const phoneTrim = (phone || "").trim().replace(/\s/g, "");
    if (!phoneTrim) next.phone = "Phone number is required";
    else if (!isValidPhone(phoneTrim)) next.phone = "Enter a valid 10-digit phone number";
    if (deliveryMethod === "home_delivery") {
      const addrTrim = (address || "").trim();
      if (addrTrim.length < 10) next.address = "Enter a complete delivery address (at least 10 characters)";
    }
    if (deliveryMethod === "store_pickup" && !selectedStore) {
      next.store = "Please select a store";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }, [name, phone, address, deliveryMethod, selectedStore]);

  const orderPayload = useCallback(
    () => ({
      session_id: sessionId,
      user_id: sessionId,
      items: cart.map((p) => ({ product_id: p.id, quantity: p.quantity ?? 1, price: p.price })),
      delivery_method: deliveryMethod,
      delivery_address: deliveryMethod === "home_delivery" ? address.trim() : null,
      store_location: deliveryMethod === "store_pickup" ? selectedStore : null,
    }),
    [sessionId, cart, deliveryMethod, address, selectedStore]
  );

  const clearCartAndRedirect = useCallback(
    (orderId: string) => {
      fetch(`${API}/session/${sessionId}/cart/clear`, { method: "POST" }).catch(() => {});
      router.push(`/orders/${orderId}?spin=1`);
    },
    [sessionId, router]
  );

  const handlePlaceOrder = async () => {
    if (!validate()) return;
    if (deliveryMethod === "store_pickup" && !selectedStore) {
      alert("Please select a store");
      return;
    }

    setLoading(true);
    setErrors({});
    try {
      const payload = orderPayload();
      const payTotal = discounts.length > 0 ? totalAfterDiscount : total;

      // Attempt Razorpay flow if configured and available
      const keyRes = await fetch(`${API}/wallet/razorpay-key`, { headers: AUTH_HEADERS() });
      const razorpayConfigured = keyRes.ok && (await keyRes.json()).key_id;

      if (razorpayConfigured && typeof window.Razorpay !== "undefined") {
        const createRes = await fetch(`${API}/checkout/create-payment`, {
          method: "POST",
          headers: AUTH_HEADERS(),
          body: JSON.stringify({ ...payload, order_total: payTotal }),
        });
        if (!createRes.ok) {
          const err = await createRes.json().catch(() => ({}));
          alert(err.detail || "Failed to create payment");
          setLoading(false);
          return;
        }
        const { razorpay_order_id, amount: amountPaise, key_id } = await createRes.json();
        const rzp = new window.Razorpay({
          key: key_id,
          amount: amountPaise,
          order_id: razorpay_order_id,
          name: "AuraShop",
          description: `Order total ${formatPrice(payTotal)}`,
          handler: async (response: { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string }) => {
            setLoading(true);
            try {
              const confirmRes = await fetch(`${API}/checkout/confirm-payment`, {
                method: "POST",
                headers: AUTH_HEADERS(),
                body: JSON.stringify({
                  razorpay_order_id: response.razorpay_order_id,
                  payment_id: response.razorpay_payment_id,
                  signature: response.razorpay_signature,
                }),
              });
              if (!confirmRes.ok) {
                const err = await confirmRes.json().catch(() => ({}));
                alert(err.detail || "Payment verification failed");
                return;
              }
              const { order_id } = await confirmRes.json();
              clearCartAndRedirect(order_id);
            } catch {
              alert("Failed to confirm order. Contact support with your payment ID.");
            } finally {
              setLoading(false);
            }
          },
        });
        rzp.open();
        setLoading(false);
        return;
      }
      const res = await fetch(`${API}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Failed to place order");
        setLoading(false);
        return;
      }
      const order = await res.json();

      // Clear cart after successful order (use user_id when logged in)
      try {
        const clearUrl = user?.user_id
          ? `${API}/session/${sessionId}/cart/clear?user_id=${encodeURIComponent(user.user_id)}`
          : `${API}/session/${sessionId}/cart/clear`;
        await fetch(clearUrl, { method: "POST" });
      } catch (e) {
        console.error("Failed to clear cart:", e);
      }
      }
      const order = await res.json();
      clearCartAndRedirect(order.id);
    } catch (err) {
      alert("Failed to place order. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="py-12 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto" />
        <p className="mt-4 text-muted-foreground">Redirecting to login...</p>
      </div>
    );
  }

  if (cart.length === 0) {
    return (
      <div className="py-12 text-center">
        <ShoppingBag className="h-16 w-16 mx-auto text-muted-foreground/50 mb-4" />
        <p className="text-lg font-medium text-muted-foreground">Your cart is empty</p>
        <Link href="/products">
          <Button className="mt-4">Browse Products</Button>
        </Link>
      </div>
    );
  }

  return (
    <>
      <Script src="https://checkout.razorpay.com/v1/checkout.js" strategy="lazyOnload" />
    <div className="py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/cart">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">Checkout</h1>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Name <span className="text-red-500">*</span></label>
                <Input
                  placeholder="Your full name"
                  value={name}
                  onChange={(e) => { setName(e.target.value); setErrors((prev) => ({ ...prev, name: undefined })); }}
                  className={`mt-1 ${errors.name ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                  maxLength={100}
                />
                {errors.name && <p className="text-sm text-red-500 mt-1">{errors.name}</p>}
              </div>
              <div>
                <label className="text-sm font-medium">Phone <span className="text-red-500">*</span></label>
                <Input
                  type="tel"
                  inputMode="numeric"
                  placeholder="10-digit mobile number"
                  value={phone}
                  onChange={(e) => { setPhone(e.target.value.replace(/\D/g, "").slice(0, 12)); setErrors((prev) => ({ ...prev, phone: undefined })); }}
                  className={`mt-1 ${errors.phone ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                  maxLength={12}
                />
                {errors.phone && <p className="text-sm text-red-500 mt-1">{errors.phone}</p>}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Delivery Method</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setDeliveryMethod("home_delivery")}
                  className={`relative rounded-lg border-2 p-4 text-left transition-colors ${
                    deliveryMethod === "home_delivery"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <Home className="h-6 w-6 mb-2 text-primary" />
                  <p className="font-medium">Home Delivery</p>
                  <p className="text-xs text-muted-foreground mt-1">Delivered to your address</p>
                  {deliveryMethod === "home_delivery" && (
                    <Check className="absolute top-3 right-3 h-5 w-5 text-primary" />
                  )}
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => setDeliveryMethod("store_pickup")}
                  className={`relative rounded-lg border-2 p-4 text-left transition-colors ${
                    deliveryMethod === "store_pickup"
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <Store className="h-6 w-6 mb-2 text-primary" />
                  <p className="font-medium">Store Pickup</p>
                  <p className="text-xs text-muted-foreground mt-1">Pick up from store with QR</p>
                  {deliveryMethod === "store_pickup" && (
                    <Check className="absolute top-3 right-3 h-5 w-5 text-primary" />
                  )}
                </motion.button>
              </div>

              {deliveryMethod === "home_delivery" && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <label className="text-sm font-medium">Delivery Address <span className="text-red-500">*</span></label>
                  <Input
                    placeholder="Full address (street, city, state, PIN)"
                    value={address}
                    onChange={(e) => { setAddress(e.target.value); setErrors((prev) => ({ ...prev, address: undefined })); }}
                    className={`mt-1 ${errors.address ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                  />
                  {errors.address && <p className="text-sm text-red-500 mt-1">{errors.address}</p>}
                </motion.div>
              )}

              {deliveryMethod === "store_pickup" && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
                  <label className="text-sm font-medium">Select Store <span className="text-red-500">*</span></label>
                  {errors.store && <p className="text-sm text-red-500">{errors.store}</p>}
                  {stores.map((store) => (
                    <div
                      key={store.id}
                      onClick={() => { setSelectedStore(store.id); setErrors((prev) => ({ ...prev, store: undefined })); }}
                      className={`rounded-lg border p-3 cursor-pointer transition-colors ${
                        selectedStore === store.id
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/50"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium">{store.name}</p>
                          <p className="text-sm text-muted-foreground">{store.address}</p>
                        </div>
                        {selectedStore === store.id && <Check className="h-5 w-5 text-primary" />}
                      </div>
                    </div>
                  ))}
                </motion.div>
              )}
            </CardContent>
          </Card>
        </div>

        <div>
          <Card className="sticky top-24">
            <CardHeader>
              <CardTitle>Order Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {cart.map((item) => {
                  const qty = item.quantity ?? 1;
                  const lineTotal = item.price * qty;
                  return (
                    <div key={item.id} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">
                        {item.name}
                        {qty > 1 && <span className="ml-1">× {qty}</span>}
                      </span>
                      <span className="font-medium">{formatPrice(lineTotal)}</span>
                    </div>
                  );
                })}
              </div>
              {discounts.length > 0 && (
                <div className="space-y-2 border-t pt-4">
                  <p className="text-sm font-medium flex items-center gap-1">
                    <Tag className="h-4 w-4 text-primary" />
                    Applicable discounts
                  </p>
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {discounts.map((d) => (
                      <DiscountCard key={`${d.discount_type}-${d.product_id ?? ""}`} discount={d} />
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    You save ₹{totalDiscountAmount.toFixed(0)} (total after discounts: {formatPrice(totalAfterDiscount)})
                  </p>
                </div>
              )}

              <div className="border-t pt-4">
                <div className="flex justify-between font-bold text-fluid-lg">
                  <span>Total</span>
                  <span className="text-primary">
                    {discounts.length > 0 ? formatPrice(totalAfterDiscount) : formatPrice(total)}
                  </span>
                </div>
              </div>
              
              {cashbackPreview && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <Sparkles className="h-4 w-4 text-emerald-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
                      Earn {formatPrice(cashbackPreview.amount)} AuraPoints
                    </p>
                    <p className="text-xs text-emerald-600/80 dark:text-emerald-400/80">
                      {cashbackPreview.rate} rewards • Valid for 30 days
                    </p>
                  </div>
                </div>
              )}

              <Button
                className="w-full"
                size="lg"
                onClick={handlePlaceOrder}
                disabled={loading}
              >
                {loading ? "Processing..." : "Pay & Place Order"}
              </Button>
              <p className="text-xs text-center text-muted-foreground">
                Pay securely via Razorpay (card, UPI, net banking). If not configured, order is placed directly.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
    </>
  );
}
