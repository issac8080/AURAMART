"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ShoppingBag, Trash2, ArrowLeft, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProductCard } from "@/components/ProductCard";
import { useCart } from "@/app/providers";
import { getCart, fetchRecommendations, trackEvent } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import type { Product } from "@/lib/api";

export default function CartPage() {
  const { sessionId, refreshCart } = useCart();
  const [cart, setCart] = useState<Product[]>([]);
  const [upsells, setUpsells] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    trackEvent({
      event_type: "page_view",
      session_id: sessionId,
      metadata: { page: "cart" },
    });
  }, [sessionId]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [cartRes, recRes] = await Promise.all([
          getCart(sessionId),
          fetchRecommendations(sessionId, { limit: 4 }),
        ]);
        setCart(cartRes.cart);
        const cartIds = cartRes.cart.map((p) => p.id);
        const upsellProducts = recRes.recommendations
          .filter((r) => !cartIds.includes(r.product_id))
          .slice(0, 4)
          .map((r) => (r.product ? { ...r.product, id: r.product_id } as Product : null))
          .filter(Boolean) as Product[];
        setUpsells(upsellProducts);
      } catch {
        setCart([]);
        setUpsells([]);
      } finally {
        setLoading(false);
      }
    }
    if (sessionId) load();
  }, [sessionId]);

  const total = cart.reduce((sum, p) => sum + p.price, 0);

  const handleRemove = async (productId: string) => {
    await trackEvent({
      event_type: "cart_remove",
      session_id: sessionId,
      product_id: productId,
    });
    refreshCart();
    const { cart: updated } = await getCart(sessionId);
    setCart(updated);
  };

  const handleAddToCart = (productId: string) => {
    trackEvent({ event_type: "cart_add", session_id: sessionId, product_id: productId });
    refreshCart();
  };

  const handleProductClick = (productId: string) => {
    trackEvent({ event_type: "product_click", session_id: sessionId, product_id: productId });
  };

  if (loading) {
    return (
      <div className="py-6 sm:py-8 animate-pulse space-y-6">
        <div className="h-8 w-32 bg-muted rounded-xl" />
        <div className="h-48 sm:h-56 bg-muted rounded-2xl" />
      </div>
    );
  }

  return (
    <div className="py-4 sm:py-6 space-y-6 sm:space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="font-heading text-fluid-2xl sm:text-fluid-3xl font-bold tracking-tight">Your cart</h1>
        <Link href="/products">
          <Button variant="outline" size="sm" className="rounded-xl font-medium w-full sm:w-auto">
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            Continue shopping
          </Button>
        </Link>
      </div>

      {cart.length === 0 ? (
        <Card className="p-8 sm:p-12 text-center rounded-2xl border-border/80">
          <ShoppingBag className="h-12 w-12 sm:h-14 sm:w-14 mx-auto text-muted-foreground mb-4" />
          <p className="text-fluid-base text-muted-foreground mb-4">Your cart is empty.</p>
          <Link href="/products">
            <Button size="lg" className="rounded-xl font-medium">Browse products</Button>
          </Link>
        </Card>
      ) : (
        <>
          <div className="grid md:grid-cols-3 gap-4 sm:gap-6">
            <div className="md:col-span-2 space-y-3 sm:space-y-4">
              {cart.map((item) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex gap-3 sm:gap-4 rounded-2xl border border-border/80 p-3 sm:p-4 bg-card shadow-card hover:shadow-card-hover transition-shadow"
                >
                  <div
                    className="w-16 h-16 sm:w-20 sm:h-20 rounded-lg sm:rounded-xl bg-muted flex-shrink-0 bg-cover bg-center"
                    style={{
                      backgroundImage: item.image_url ? `url(${item.image_url})` : undefined,
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <Link href={`/products/${item.id}`} className="font-medium text-fluid-sm hover:text-primary line-clamp-1">
                      {item.name}
                    </Link>
                    <p className="text-fluid-xs text-muted-foreground">{item.category}</p>
                    <p className="font-bold text-primary text-fluid-sm">{formatPrice(item.price)}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-10 w-10 rounded-xl shrink-0"
                    onClick={() => handleRemove(item.id)}
                    aria-label="Remove from cart"
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </motion.div>
              ))}
            </div>
            <div>
              <Card className="p-4 sm:p-5 sticky top-24 rounded-xl sm:rounded-2xl border-border/80">
                <h2 className="font-heading font-bold text-fluid-lg mb-2">Order summary</h2>
                <p className="text-fluid-2xl font-bold text-primary">{formatPrice(total)}</p>
                <p className="text-fluid-sm text-muted-foreground mt-1">{cart.length} item(s)</p>
                <Link href="/checkout">
                  <Button className="w-full mt-4 rounded-xl font-medium" size="lg">
                    Proceed to checkout
                  </Button>
                </Link>
              </Card>
            </div>
          </div>

          {upsells.length > 0 && (
            <Card className="border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 p-4 sm:p-5 glass-card">
              <h2 className="font-heading font-bold text-fluid-base text-primary mb-3 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                People like you also bought
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                {upsells.map((p) => (
                  <ProductCard
                    key={p.id}
                    product={p}
                    sessionId={sessionId}
                    onAddToCart={handleAddToCart}
                    trackClick={handleProductClick}
                  />
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
