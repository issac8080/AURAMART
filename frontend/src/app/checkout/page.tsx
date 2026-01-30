"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ShoppingBag, Home, Store, Check, ArrowLeft, Sparkles, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useCart } from "@/app/providers";
import { formatPrice } from "@/lib/utils";
import Link from "next/link";

const API = "/api";

type Store = {
  id: string;
  name: string;
  address: string;
};

export default function CheckoutPage() {
  const router = useRouter();
  const { sessionId } = useCart();
  const [cart, setCart] = useState<any[]>([]);
  const [deliveryMethod, setDeliveryMethod] = useState<"home_delivery" | "store_pickup">("home_delivery");
  const [stores, setStores] = useState<Store[]>([]);
  const [selectedStore, setSelectedStore] = useState("");
  const [address, setAddress] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [cashbackPreview, setCashbackPreview] = useState<{ amount: number; rate: string } | null>(null);

  const total = cart.reduce((sum, p) => sum + p.price, 0);

  useEffect(() => {
    async function loadCart() {
      try {
        const res = await fetch(`${API}/session/${sessionId}/cart`);
        const data = await res.json();
        setCart(data.cart || []);
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
  }, [sessionId]);

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

  const handlePlaceOrder = async () => {
    if (!name || !phone) {
      alert("Please enter your name and phone number");
      return;
    }
    if (deliveryMethod === "home_delivery" && !address) {
      alert("Please enter delivery address");
      return;
    }
    if (deliveryMethod === "store_pickup" && !selectedStore) {
      alert("Please select a store");
      return;
    }

    setLoading(true);
    try {
      const userId = sessionId; // In production, use actual user ID
      const res = await fetch(`${API}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          user_id: userId,
          items: cart.map((p) => ({ product_id: p.id, quantity: 1, price: p.price })),
          delivery_method: deliveryMethod,
          delivery_address: deliveryMethod === "home_delivery" ? address : null,
          store_location: deliveryMethod === "store_pickup" ? selectedStore : null,
        }),
      });
      const order = await res.json();
      
      // Clear cart after successful order
      try {
        await fetch(`${API}/session/${sessionId}/cart/clear`, {
          method: "POST",
        });
      } catch (e) {
        console.error("Failed to clear cart:", e);
      }
      
      router.push(`/orders/${order.id}?spin=1`);
    } catch (err) {
      alert("Failed to place order. Please try again.");
    } finally {
      setLoading(false);
    }
  };

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
                <label className="text-sm font-medium">Name</label>
                <Input
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Phone</label>
                <Input
                  type="tel"
                  placeholder="Phone number"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="mt-1"
                />
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
                  <label className="text-sm font-medium">Delivery Address</label>
                  <Input
                    placeholder="Enter your full address"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    className="mt-1"
                  />
                </motion.div>
              )}

              {deliveryMethod === "store_pickup" && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
                  <label className="text-sm font-medium">Select Store</label>
                  {stores.map((store) => (
                    <div
                      key={store.id}
                      onClick={() => setSelectedStore(store.id)}
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
                {cart.map((item) => (
                  <div key={item.id} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{item.name}</span>
                    <span className="font-medium">{formatPrice(item.price)}</span>
                  </div>
                ))}
              </div>
              <div className="border-t pt-4">
                <div className="flex justify-between font-bold text-fluid-lg">
                  <span>Total</span>
                  <span className="text-primary">{formatPrice(total)}</span>
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
                {loading ? "Placing Order..." : "Place Order"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
