"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, TrendingUp, Zap, MessageCircle, ChevronDown } from "lucide-react";
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

  const scrollToPicks = () => {
    document.getElementById("recommended-picks")?.scrollIntoView({ behavior: "smooth" });
  };

  const openChat = () => {
    const event = new CustomEvent("open-aurashop-chat");
    window.dispatchEvent(event);
  };

  const recBadges: ("best_match" | "value" | "trending" | null)[] = recommended.map((_, i) =>
    i === 0 ? "best_match" : i === 1 ? "value" : i === 2 ? "trending" : null
  );
  const trendBadges: ("best_match" | "value" | "trending" | null)[] = trending.map((_, i) =>
    i === 0 ? "trending" : null
  );

  return (
    <div className="space-y-10 sm:space-y-14 py-4 sm:py-6 lg:py-8">
      {/* Large hero with animated gradient + glassmorphism */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="relative min-h-[420px] sm:min-h-[480px] lg:min-h-[520px] rounded-2xl sm:rounded-3xl overflow-hidden"
      >
        {/* Animated gradient background */}
        <div
          className="absolute inset-0 animate-gradient"
          style={{
            background: "linear-gradient(135deg, rgba(99, 102, 241, 0.92) 0%, rgba(139, 92, 246, 0.9) 35%, rgba(59, 130, 246, 0.88) 70%, rgba(99, 102, 241, 0.92) 100%",
          }}
        />
        <div
          className="absolute inset-0 opacity-40"
          style={{
            backgroundImage: `url(${getHeroBackground()})`,
            backgroundSize: "cover",
            backgroundPosition: "center",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent pointer-events-none" />

        <div className="relative z-10 h-full flex flex-col justify-center px-5 py-12 sm:p-12 md:px-16 md:py-16 lg:px-20 lg:py-20 text-white">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4 }}
            className="max-w-2xl"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 glass rounded-full px-4 py-2 mb-6"
            >
              <Sparkles className="h-4 w-4 text-cyan-300" />
              <span className="text-sm font-semibold">AI-Powered Shopping</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25, duration: 0.45 }}
              className="font-heading text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-4 leading-[1.08]"
            >
              Discover Your
              <br />
              <span className="bg-white/20 backdrop-blur-sm px-1 rounded">Perfect Style</span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
              className="text-lg sm:text-xl text-white/90 max-w-xl mb-8 leading-relaxed"
            >
              Personalized recommendations powered by AI. Find exactly what you need, when you need it.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45 }}
              className="flex flex-wrap gap-3 sm:gap-4"
            >
              <motion.button
                onClick={openChat}
                whileHover={{ scale: 1.03, boxShadow: "0 0 32px -4px rgba(34, 211, 238, 0.4)" }}
                whileTap={{ scale: 0.98 }}
                className="inline-flex items-center gap-2 rounded-2xl bg-white text-indigo-600 px-5 py-3 sm:px-6 sm:py-3.5 font-semibold shadow-xl hover:bg-white/95 transition-colors"
              >
                <MessageCircle className="h-5 w-5" />
                Ask AI
              </motion.button>
              <motion.button
                onClick={scrollToPicks}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
                className="inline-flex items-center gap-2 rounded-2xl glass border-white/30 px-5 py-3 sm:px-6 sm:py-3.5 font-semibold hover:bg-white/20 transition-colors"
              >
                Explore Picks
                <ChevronDown className="h-5 w-5" />
              </motion.button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.55 }}
              className="flex flex-wrap gap-2 sm:gap-3 mt-8"
            >
              <div className="flex items-center gap-2 glass rounded-full px-3.5 py-2">
                <Zap className="h-3.5 w-3.5 text-cyan-300" />
                <span className="text-sm font-medium">Smart Recommendations</span>
              </div>
              <div className="flex items-center gap-2 glass rounded-full px-3.5 py-2">
                <TrendingUp className="h-3.5 w-3.5 text-cyan-300" />
                <span className="text-sm font-medium">Trending Picks</span>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </motion.section>

      <FestivalBanner />

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.05 }}
              className="aspect-[3/4] sm:h-80 rounded-2xl sm:rounded-3xl bg-muted/60 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <>
          <div id="recommended-picks" className="scroll-mt-6">
            <ProductCarousel
              title="✨ Recommended for You"
              products={recommended}
              badges={recBadges}
              sessionId={sessionId}
              onAddToCart={handleAddToCart}
              onProductClick={handleProductClick}
            />
          </div>
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
