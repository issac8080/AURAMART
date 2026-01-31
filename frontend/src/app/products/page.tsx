"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ProductCard } from "@/components/ProductCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sparkles, SlidersHorizontal, ShoppingBag } from "lucide-react";
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
  const [minPrice, setMinPrice] = useState<string>(() => searchParams.get("min_price") ?? "");
  const [maxPrice, setMaxPrice] = useState<string>(() => searchParams.get("max_price") ?? "");
  const [minRating, setMinRating] = useState<string>(() => searchParams.get("min_rating") ?? "");
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
    if (searchParams.get("min_price") != null) setMinPrice(searchParams.get("min_price") ?? "");
    if (searchParams.get("max_price") != null) setMaxPrice(searchParams.get("max_price") ?? "");
    if (searchParams.get("min_rating") != null) setMinRating(searchParams.get("min_rating") ?? "");
  }, [categoryFromUrl, searchParams]);

  const router = useRouter();

  const updateUrl = useCallback(
    (updates: { category?: string; min_price?: string; max_price?: string; min_rating?: string }) => {
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      if (updates.category !== undefined) (updates.category ? params.set("category", updates.category) : params.delete("category"));
      if (updates.min_price !== undefined) (updates.min_price ? params.set("min_price", updates.min_price) : params.delete("min_price"));
      if (updates.max_price !== undefined) (updates.max_price ? params.set("max_price", updates.max_price) : params.delete("max_price"));
      if (updates.min_rating !== undefined) (updates.min_rating ? params.set("min_rating", updates.min_rating) : params.delete("min_rating"));
      const q = params.toString();
      router.replace(q ? `/products?${q}` : "/products", { scroll: false });
    },
    [router, searchParams]
  );

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
          fetchRecommendations(sessionId || "", { limit: 4 }),
        ]);
        setProducts(res.products ?? []);
        const picks = (recRes.recommendations ?? [])
          .map((r) => (r.product ? { ...r.product, id: r.product_id } as Product : null))
          .filter(Boolean) as Product[];
        setTopPicks(picks);
      } catch {
        const res = await fetchProducts({
          category: category || undefined,
          min_price: minPrice ? Number(minPrice) : undefined,
          max_price: maxPrice ? Number(maxPrice) : undefined,
          min_rating: minRating ? Number(minRating) : undefined,
          limit: 200,
        });
        setProducts(res.products ?? []);
        setTopPicks([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [sessionId, category, minPrice, maxPrice, minRating]);

  const handleCategoryChange = (value: string) => {
    setCategory(value);
    updateUrl({ category: value || undefined });
  };
  const handleMinPriceChange = (value: string) => {
    setMinPrice(value);
    updateUrl({ min_price: value || undefined });
  };
  const handleMaxPriceChange = (value: string) => {
    setMaxPrice(value);
    updateUrl({ max_price: value || undefined });
  };
  const handleMinRatingChange = (value: string) => {
    setMinRating(value);
    updateUrl({ min_rating: value || undefined });
  };

  const handleAddToCart = async (productId: string) => {
    try {
      await trackEvent({ event_type: "cart_add", session_id: sessionId, product_id: productId });
      await refreshCart();
    } catch (error) {
      console.error("Failed to add to cart:", error);
    }
  };

  const handleProductClick = (productId: string) => {
    trackEvent({ event_type: "product_click", session_id: sessionId, product_id: productId });
  };

  const categoryList = categories.length > 0 ? categories : ["Clothing", "Electronics", "Accessories", "Footwear"];

  return (
    <div className="py-6 sm:py-8 lg:py-10 space-y-8 sm:space-y-10">
      {/* Page header – premium */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-gray-900 dark:text-white">
          Products
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Browse with smart filters and AI-powered picks
        </p>
      </motion.div>

      {/* Top picks – AI section */}
      {topPicks.length > 0 && (
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="rounded-2xl sm:rounded-3xl border-2 border-indigo-200 dark:border-indigo-900/50 bg-gradient-to-br from-indigo-50/80 to-purple-50/60 dark:from-indigo-950/40 dark:to-purple-950/30 p-5 sm:p-6 shadow-lg shadow-indigo-500/10 overflow-hidden"
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/20">
              <Sparkles className="h-4 w-4" />
            </div>
            <h2 className="font-heading text-lg sm:text-xl font-bold text-indigo-700 dark:text-indigo-300">
              Top picks based on your browsing
            </h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            AI recommendations just for you
          </p>
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

      {/* Main content: filters + grid */}
      <section className="flex flex-col md:flex-row gap-6 lg:gap-8">
        {/* Filters sidebar – premium card */}
        <motion.aside
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
          className="md:w-64 flex-shrink-0"
        >
          <div className="rounded-2xl border-2 border-indigo-100 dark:border-indigo-900/40 bg-gradient-to-b from-white to-indigo-50/30 dark:from-gray-900/80 dark:to-indigo-950/20 shadow-xl shadow-indigo-500/5 overflow-hidden sticky top-24">
            <div className="h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500" />
            <div className="p-5 space-y-5">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-5 w-5 text-indigo-500" />
                <h3 className="font-heading font-bold text-gray-900 dark:text-white">Filters</h3>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Category</label>
                <select
                  value={category}
                  onChange={(e) => handleCategoryChange(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border-2 border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2.5 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none transition-colors"
                >
                  <option value="">All</option>
                  {categoryList.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Min price (₹)</label>
                <Input
                  type="number"
                  placeholder="0"
                  value={minPrice}
                  onChange={(e) => setMinPrice(e.target.value)}
                  className="mt-1.5 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Max price (₹)</label>
                <Input
                  type="number"
                  placeholder="Any"
                  value={maxPrice}
                  onChange={(e) => handleMaxPriceChange(e.target.value)}
                  className="mt-1.5 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Min rating</label>
                <Input
                  type="number"
                  min={0}
                  max={5}
                  step={0.5}
                  placeholder="0"
                  value={minRating}
                  onChange={(e) => setMinRating(e.target.value)}
                  className="mt-1.5 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                />
              </div>
            </div>
          </div>
        </motion.aside>

        {/* Product grid */}
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
              {[...Array(8)].map((_, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  className="aspect-[3/4] sm:min-h-[280px] rounded-2xl border border-gray-200 dark:border-gray-700 bg-gradient-to-b from-gray-100 to-gray-50 dark:from-gray-800/50 dark:to-gray-800/30 animate-pulse"
                />
              ))}
            </div>
          ) : products.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="relative overflow-hidden rounded-3xl border-2 border-dashed border-indigo-200 dark:border-indigo-800/50 bg-gradient-to-br from-indigo-50/60 to-purple-50/40 dark:from-gray-900/80 dark:to-indigo-950/30 shadow-xl shadow-gray-200/50 dark:shadow-none"
            >
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(99,102,241,0.12),transparent)] pointer-events-none" />
              <div className="relative p-10 sm:p-14 text-center">
                <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30 mb-6">
                  <ShoppingBag className="h-10 w-10" />
                </div>
                <h3 className="font-heading text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  No products match your filters
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-8 max-w-sm mx-auto">
                  Try adjusting category, price range, or rating to see more results.
                </p>
                <Button
                  variant="outline"
                  size="lg"
                  className="rounded-xl font-semibold border-2 border-indigo-300 dark:border-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-500/10"
                  onClick={() => {
                    setCategory("");
                    setMinPrice("");
                    setMaxPrice("");
                    setMinRating("");
                    updateUrl({ category: undefined, min_price: undefined, max_price: undefined, min_rating: undefined });
                  }}
                >
                  Clear filters
                </Button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25 }}
              className="space-y-4"
            >
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                {products.length} product{products.length !== 1 ? "s" : ""} found
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-5">
                {products.map((product, i) => (
                  <motion.div
                    key={product.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.02, 0.2) }}
                  >
                    <ProductCard
                      product={product}
                      sessionId={sessionId}
                      onAddToCart={handleAddToCart}
                      trackClick={handleProductClick}
                    />
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </section>
    </div>
  );
}
