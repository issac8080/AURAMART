"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ShoppingBag, Trash2, ArrowLeft, Sparkles, ShoppingCart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProductCard } from "@/components/ProductCard";
import { useCart } from "@/app/providers";
import { getCart, fetchRecommendations, trackEvent } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { getProductImageSrc, getProductImagePlaceholder } from "@/lib/unsplash";
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
      <div className="py-6 sm:py-8 space-y-6">
        <div className="flex justify-between items-center">
          <div className="h-9 w-40 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
          <div className="h-10 w-36 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse" />
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-28 rounded-2xl bg-gray-100 dark:bg-gray-800/50 animate-pulse" />
            ))}
          </div>
          <div className="h-48 rounded-2xl bg-gray-100 dark:bg-gray-800/50 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="py-6 sm:py-8 lg:py-10 space-y-8 sm:space-y-10">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-gray-900 dark:text-white">
            Your cart
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {cart.length === 0 ? "No items yet" : `${cart.length} item${cart.length === 1 ? "" : "s"} in your cart`}
          </p>
        </div>
        <Link href="/products" className="inline-flex shrink-0">
          <Button
            variant="outline"
            size="sm"
            className="rounded-xl font-semibold w-full sm:w-auto border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-indigo-400/50"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Continue shopping
          </Button>
        </Link>
      </div>

      {cart.length === 0 ? (
        /* Empty state – inviting, not pale */
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="relative overflow-hidden rounded-3xl border border-gray-200 dark:border-gray-700 bg-gradient-to-br from-gray-50 to-indigo-50/30 dark:from-gray-900/80 dark:to-indigo-950/20 shadow-xl shadow-gray-200/50 dark:shadow-none"
        >
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(99,102,241,0.15),transparent)] pointer-events-none" />
          <div className="relative p-10 sm:p-14 text-center">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30 mb-6">
              <ShoppingBag className="h-10 w-10" />
            </div>
            <h2 className="font-heading text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Your cart is empty
            </h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto mb-8">
              Add items from the store and they’ll show up here. Check out recommendations to get started.
            </p>
            <Link href="/products">
              <Button
                size="lg"
                className="rounded-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 shadow-lg shadow-indigo-500/25 text-white border-0"
              >
                <ShoppingCart className="h-5 w-5 mr-2" />
                Browse products
              </Button>
            </Link>
          </div>
        </motion.div>
      ) : (
        <>
          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            {/* Cart items */}
            <div className="md:col-span-2 space-y-4">
              <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Cart items
              </h2>
              <div className="space-y-4">
                {cart.map((item, i) => (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="group flex gap-4 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50 p-4 shadow-sm hover:shadow-md hover:border-indigo-200 dark:hover:border-indigo-900/50 transition-all duration-200"
                  >
                    <Link href={`/products/${item.id}`} className="flex-shrink-0 overflow-hidden rounded-xl bg-gray-100 dark:bg-gray-800 w-20 h-20 sm:w-24 sm:h-24 block">
                      <img
                        src={getProductImageSrc(item.image_url, item.category, item.id, item.name)}
                        alt={item.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.src = getProductImagePlaceholder(item.name);
                        }}
                      />
                    </Link>
                    <div className="flex-1 min-w-0">
                      <Link
                        href={`/products/${item.id}`}
                        className="font-semibold text-gray-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 line-clamp-2 transition-colors"
                      >
                        {item.name}
                      </Link>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{item.category}</p>
                      <p className="font-bold text-indigo-600 dark:text-indigo-400 text-lg mt-2">
                        {formatPrice(item.price)}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-10 w-10 rounded-xl shrink-0 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                      onClick={() => handleRemove(item.id)}
                      aria-label="Remove from cart"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Order summary – sticky, clear CTA */}
            <div className="md:col-span-1">
              <div className="sticky top-24">
                <Card className="rounded-2xl border-2 border-indigo-200 dark:border-indigo-900/50 bg-gradient-to-b from-white to-indigo-50/20 dark:from-gray-900 dark:to-indigo-950/20 shadow-xl shadow-indigo-500/10 overflow-hidden">
                  <div className="h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500" />
                  <CardContent className="p-5 sm:p-6">
                    <h2 className="font-heading text-lg font-bold text-gray-900 dark:text-white mb-4">
                      Order summary
                    </h2>
                    <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
                      <span>Subtotal ({cart.length} items)</span>
                      <span>{formatPrice(total)}</span>
                    </div>
                    <div className="border-t border-gray-200 dark:border-gray-700 my-4 pt-4">
                      <div className="flex justify-between items-baseline">
                        <span className="font-semibold text-gray-900 dark:text-white">Total</span>
                        <span className="font-heading text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                          {formatPrice(total)}
                        </span>
                      </div>
                    </div>
                    <Link href="/checkout" className="block mt-5">
                      <Button
                        className="w-full rounded-xl font-semibold h-12 bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 shadow-lg shadow-indigo-500/25 text-white border-0"
                        size="lg"
                      >
                        Proceed to checkout
                      </Button>
                    </Link>
                    <p className="text-xs text-gray-500 dark:text-gray-400 text-center mt-3">
                      Secure checkout · No extra fees
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>

          {/* Upsells – AI section with strong contrast */}
          {upsells.length > 0 && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="rounded-3xl border border-indigo-200 dark:border-indigo-900/50 bg-gradient-to-br from-indigo-50/80 to-purple-50/60 dark:from-indigo-950/40 dark:to-purple-950/30 p-6 sm:p-8 shadow-lg shadow-indigo-500/10"
            >
              <h2 className="font-heading text-lg sm:text-xl font-bold text-indigo-700 dark:text-indigo-300 mb-1 flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-500" />
                People like you also bought
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                AI picks based on your cart
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
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
            </motion.section>
          )}
        </>
      )}
    </div>
  );
}
