"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { ProductCard } from "@/components/ProductCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCart } from "@/app/providers";
import { fetchProducts, fetchCategories, fetchRecommendations, trackEvent } from "@/lib/api";
import type { Product } from "@/lib/api";

export default function ProductsPage() {
  const searchParams = useSearchParams();
  const categoryFromUrl = searchParams.get("category") ?? "";
  const { sessionId, refreshCart } = useCart();
  const [products, setProducts] = useState<Product[]>([]);
  const [topPicks, setTopPicks] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState<string>(categoryFromUrl);
  const [minPrice, setMinPrice] = useState<string>("");
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [minRating, setMinRating] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    trackEvent({
      event_type: "page_view",
      session_id: sessionId,
      metadata: { page: "products" },
    });
  }, [sessionId]);

  useEffect(() => {
    fetchCategories().then((r) => setCategories(r.categories));
  }, []);

  useEffect(() => {
    setCategory(categoryFromUrl);
  }, [categoryFromUrl]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [res, recRes] = await Promise.all([
          fetchProducts({
            category: category || undefined,
            min_price: minPrice ? Number(minPrice) : undefined,
            max_price: maxPrice ? Number(maxPrice) : undefined,
            min_rating: minRating ? Number(minRating) : undefined,
            limit: 200,
          }),
          fetchRecommendations(sessionId, { limit: 4 }),
        ]);
        setProducts(res.products);
        const picks = recRes.recommendations
          .map((r) => (r.product ? { ...r.product, id: r.product_id } as Product : null))
          .filter(Boolean) as Product[];
        setTopPicks(picks);
      } catch {
        const res = await fetchProducts({ limit: 200 });
        setProducts(res.products);
        setTopPicks([]);
      } finally {
        setLoading(false);
      }
    }
    if (sessionId) load();
  }, [sessionId, category, minPrice, maxPrice, minRating]);

  const handleAddToCart = (productId: string) => {
    trackEvent({ event_type: "cart_add", session_id: sessionId, product_id: productId });
    refreshCart();
  };

  const handleProductClick = (productId: string) => {
    trackEvent({ event_type: "product_click", session_id: sessionId, product_id: productId });
  };

  const categoryList = categories.length > 0 ? categories : ["Clothing", "Electronics", "Accessories", "Footwear"];

  return (
    <div className="py-4 sm:py-6 space-y-5 sm:space-y-6">
      <div>
        <h1 className="font-heading text-fluid-2xl sm:text-fluid-3xl font-bold tracking-tight">Products</h1>
        <p className="text-fluid-sm text-muted-foreground mt-0.5">Browse with smart filters</p>
      </div>

      {topPicks.length > 0 && (
        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-xl sm:rounded-2xl border border-primary/20 bg-primary/5 p-4"
        >
          <h2 className="font-heading font-bold text-fluid-sm text-primary mb-3">Top picks based on your browsing</h2>
          <div className="flex gap-3 sm:gap-4 overflow-x-auto pb-2 scrollbar-hide">
            {topPicks.map((p) => (
              <div key={p.id} className="flex-shrink-0 w-[165px] sm:w-[200px]">
                <ProductCard
                  product={p}
                  sessionId={sessionId}
                  onAddToCart={handleAddToCart}
                  trackClick={handleProductClick}
                />
              </div>
            ))}
          </div>
        </motion.section>
      )}

      <section className="flex flex-col md:flex-row gap-4 sm:gap-6">
        <aside className="md:w-56 flex-shrink-0 space-y-4 p-4 sm:p-0 rounded-xl sm:rounded-none bg-muted/40 sm:bg-transparent border border-border/60 sm:border-0">
          <div>
            <label className="text-fluid-sm font-medium">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-input bg-background px-3 py-2.5 text-fluid-sm"
            >
              <option value="">All</option>
              {categoryList.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-fluid-sm font-medium">Min price (₹)</label>
            <Input
              type="number"
              placeholder="0"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              className="mt-1.5 rounded-xl"
            />
          </div>
          <div>
            <label className="text-fluid-sm font-medium">Max price (₹)</label>
            <Input
              type="number"
              placeholder="Any"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              className="mt-1.5 rounded-xl"
            />
          </div>
          <div>
            <label className="text-fluid-sm font-medium">Min rating</label>
            <Input
              type="number"
              min={0}
              max={5}
              step={0.5}
              placeholder="0"
              value={minRating}
              onChange={(e) => setMinRating(e.target.value)}
              className="mt-1.5 rounded-xl"
            />
          </div>
        </aside>

        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="aspect-[3/4] sm:h-72 rounded-xl sm:rounded-2xl bg-muted/80 animate-pulse" />
              ))}
            </div>
          ) : products.length === 0 ? (
            <p className="text-fluid-base text-muted-foreground py-12 text-center">No products match your filters.</p>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4"
            >
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  sessionId={sessionId}
                  onAddToCart={handleAddToCart}
                  trackClick={handleProductClick}
                />
              ))}
            </motion.div>
          )}
        </div>
      </section>
    </div>
  );
}
