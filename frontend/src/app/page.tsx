"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, TrendingUp, Zap } from "lucide-react";
import { ProductCarousel } from "@/components/ProductCarousel";
import { FestivalBanner } from "@/discountFrontend/FestivalBanner";
import { useCart } from "@/app/providers";
import { fetchProducts, fetchRecommendations, trackEvent } from "@/lib/api";
import { getHeroBackground } from "@/lib/unsplash";
import type { Product } from "@/lib/api";

export default function HomePage() {
  const { sessionId, refreshCart } = useCart();
  const [recommended, setRecommended] = useState<Product[]>([]);
  const [trending, setTrending] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    trackEvent({
      event_type: "page_view",
      session_id: sessionId,
      metadata: { page: "home" },
    });
  }, [sessionId]);

  useEffect(() => {
    async function load() {
      try {
        const [recRes, productsRes] = await Promise.all([
          fetchRecommendations(sessionId, { limit: 8 }),
          fetchProducts({ limit: 15 }),
        ]);
        const recProducts = recRes.recommendations
          .map((r) => (r.product ? { ...r.product, id: r.product_id } as Product : null))
          .filter(Boolean) as Product[];
        if (recProducts.length < 5) {
          const all = productsRes.products;
          const byRating = [...all].sort((a, b) => b.rating - a.rating).slice(0, 8);
          setRecommended(byRating);
        } else {
          setRecommended(recProducts);
        }
        const byReviews = [...productsRes.products].sort((a, b) => b.review_count - a.review_count).slice(0, 10);
        setTrending(byReviews);
      } catch {
        const { products } = await fetchProducts({ limit: 15 });
        const byRating = [...products].sort((a, b) => b.rating - a.rating).slice(0, 8);
        setRecommended(byRating);
        setTrending([...products].sort((a, b) => b.review_count - a.review_count).slice(0, 10));
      } finally {
        setLoading(false);
      }
    }
    if (sessionId) load();
  }, [sessionId]);

  const handleAddToCart = (productId: string) => {
    trackEvent({ event_type: "cart_add", session_id: sessionId, product_id: productId });
    refreshCart();
  };

  const handleProductClick = (productId: string) => {
    trackEvent({ event_type: "product_click", session_id: sessionId, product_id: productId });
  };

  const recBadges: ("best_match" | "value" | "trending" | null)[] = recommended.map((_, i) =>
    i === 0 ? "best_match" : i === 1 ? "value" : i === 2 ? "trending" : null
  );
  const trendBadges: ("best_match" | "value" | "trending" | null)[] = trending.map((_, i) =>
    i === 0 ? "trending" : null
  );

  return (
    <div className="space-y-10 py-6">
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative rounded-3xl overflow-hidden border shadow-2xl"
        style={{
          backgroundImage: `linear-gradient(135deg, rgba(139, 92, 246, 0.95) 0%, rgba(168, 85, 247, 0.9) 100%), url(${getHeroBackground()})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div className="relative z-10 p-8 md:p-16 text-white">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-2 mb-4">
              <Sparkles className="h-4 w-4" />
              <span className="text-sm font-medium">AI-Powered Shopping</span>
            </div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-4">
              Discover Your
              <br />
              Perfect Style
            </h1>
            <p className="text-lg md:text-xl text-white/90 max-w-xl mb-6">
              Personalized recommendations powered by AI. Find exactly what you need, when you need it.
            </p>
            <div className="flex flex-wrap gap-3">
              <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-2">
                <Zap className="h-4 w-4" />
                <span className="text-sm font-medium">Smart Recommendations</span>
              </div>
              <div className="flex items-center gap-2 bg-white/20 backdrop-blur-sm rounded-full px-4 py-2">
                <TrendingUp className="h-4 w-4" />
                <span className="text-sm font-medium">Trending Picks</span>
              </div>
            </div>
          </motion.div>
        </div>
        <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent pointer-events-none" />
      </motion.section>

      <FestivalBanner />

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-72 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : (
        <>
          <ProductCarousel
            title="✨ Recommended for You"
            products={recommended}
            badges={recBadges}
            sessionId={sessionId}
            onAddToCart={handleAddToCart}
            onProductClick={handleProductClick}
          />
          <ProductCarousel
            title="🔥 Trending Now"
            products={trending}
            badges={trendBadges}
            sessionId={sessionId}
            onAddToCart={handleAddToCart}
            onProductClick={handleProductClick}
          />
        </>
      )}
    </div>
  );
}
