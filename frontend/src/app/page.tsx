"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  TrendingUp,
  MessageCircle,
  ChevronDown,
  ShoppingCart,
  Laptop,
  ShoppingBag,
  Package,
  Home,
  Gift,
  Ticket,
  Trophy,
  Scissors,
  PackageCheck,
  RotateCcw,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import { ProductCarousel } from "@/components/ProductCarousel";
import { HomeSpinWheel } from "@/components/HomeSpinWheel";
import { HomeJackpot } from "@/components/HomeJackpot";
import { HomeScratch } from "@/components/HomeScratch";
import { useCart } from "@/app/providers";
import {
  fetchProducts,
  fetchRecommendations,
  fetchCategories,
  fetchUserOrders,
  playCouponGame,
  playJackpot,
  playScratch,
  trackEvent,
  type Product,
  type Order,
} from "@/lib/api";
import { getHeroBackground } from "@/lib/unsplash";
import { formatPrice } from "@/lib/utils";

const FALLBACK_CATEGORIES = [
  "Electronics",
  "Clothing",
  "Accessories",
  "Footwear",
  "Watches",
  "Mobile",
  "Home",
  "Books",
  "Toys",
  "Beauty",
  "Sports",
  "Automotive",
];

function getCategoryIcon(category: string): LucideIcon {
  const c = category.toLowerCase();
  if (c.includes("electron") || c.includes("laptop") || c.includes("mobile") || c.includes("phone")) return Laptop;
  if (c.includes("cloth") || c.includes("fashion") || c.includes("wear")) return ShoppingBag;
  if (c.includes("accessor") || c.includes("bag")) return ShoppingBag;
  if (c.includes("foot") || c.includes("shoe")) return Package;
  if (c.includes("watch")) return Package;
  if (c.includes("home")) return Home;
  return Sparkles;
}

export default function HomePage() {
  const { sessionId, refreshCart } = useCart();
  const [recommended, setRecommended] = useState<Product[]>([]);
  const [trending, setTrending] = useState<Product[]>([]);
  const [premium, setPremium] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [categoryProducts, setCategoryProducts] = useState<Record<string, Product[]>>({});
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [gameResult, setGameResult] = useState<{
    played: boolean;
    won: boolean;
    code: string | null;
    min_order: number;
    discount: number;
    message: string;
  } | null>(null);
  const [gameResultJackpot, setGameResultJackpot] = useState<{
    played: boolean;
    won: boolean;
    code: string | null;
    min_order: number;
    discount: number;
    message: string;
  } | null>(null);
  const [gameResultScratch, setGameResultScratch] = useState<{
    played: boolean;
    won: boolean;
    code: string | null;
    min_order: number;
    discount: number;
    message: string;
  } | null>(null);
  const [gameLoading, setGameLoading] = useState<"spin" | "jackpot" | "scratch" | null>(null);
  const [gameModal, setGameModal] = useState<"spin" | "jackpot" | "scratch" | null>(null);

  useEffect(() => {
    fetchCategories()
      .then((r) => setCategories(r.categories?.length ? r.categories : FALLBACK_CATEGORIES))
      .catch(() => setCategories(FALLBACK_CATEGORIES));
  }, []);

  useEffect(() => {
    trackEvent({ event_type: "page_view", session_id: sessionId, metadata: { page: "home" } });
  }, [sessionId]);

  const loadAll = useCallback(async () => {
    try {
      const [recRes, productsRes, premiumRes, ordersRes] = await Promise.all([
        sessionId ? fetchRecommendations(sessionId, { limit: 10 }) : Promise.resolve({ recommendations: [] }),
        fetchProducts({ limit: 20 }),
        fetchProducts({ min_price: 50000, limit: 10 }).catch(() => ({ products: [] })),
        sessionId ? fetchUserOrders(sessionId).catch(() => ({ orders: [] })) : Promise.resolve({ orders: [] }),
      ]);
      const recProducts = (recRes.recommendations || [])
        .map((r) => (r.product ? { ...r.product, id: r.product_id } as Product : null))
        .filter(Boolean) as Product[];
      const products = productsRes.products || [];
      if (recProducts.length < 5 && products.length > 0) {
        const byRating = [...products].sort((a, b) => b.rating - a.rating).slice(0, 10);
        setRecommended(byRating);
      } else {
        setRecommended(recProducts.length > 0 ? recProducts : products.slice(0, 10));
      }
      setTrending(
        products.length > 0 ? [...products].sort((a, b) => b.review_count - a.review_count).slice(0, 12) : []
      );
      setPremium((premiumRes.products || []).slice(0, 10));
      setOrders((ordersRes.orders || []).slice(0, 3));
      const cats = categories.length > 0 ? categories.slice(0, 4) : FALLBACK_CATEGORIES.slice(0, 4);
      const byCat: Record<string, Product[]> = {};
      await Promise.all(
        cats.map(async (cat) => {
          const res = await fetchProducts({ category: cat, limit: 8 }).catch(() => ({ products: [] }));
          byCat[cat] = res.products || [];
        })
      );
      setCategoryProducts(byCat);
    } catch {
      try {
        const { products } = await fetchProducts({ limit: 20 });
        const list = products || [];
        setRecommended([...list].sort((a, b) => b.rating - a.rating).slice(0, 10));
        setTrending([...list].sort((a, b) => b.review_count - a.review_count).slice(0, 12));
        setPremium([]);
        setOrders([]);
      } catch {
        setRecommended([]);
        setTrending([]);
        setPremium([]);
        setOrders([]);
      }
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    const cats = categories.length > 0 ? categories.slice(0, 4) : FALLBACK_CATEGORIES.slice(0, 4);
    if (cats.length === 0) return;
    let cancelled = false;
    Promise.all(
      cats.map(async (cat) => {
        const res = await fetchProducts({ category: cat, limit: 8 }).catch(() => ({ products: [] }));
        return [cat, res.products || []] as const;
      })
    ).then((results) => {
      if (cancelled) return;
      const byCat: Record<string, Product[]> = {};
      results.forEach(([cat, prods]) => {
        byCat[cat] = prods;
      });
      setCategoryProducts(byCat);
    });
    return () => {
      cancelled = true;
    };
  }, [categories]);

  const handleAddToCart = (productId: string) => {
    trackEvent({ event_type: "cart_add", session_id: sessionId, product_id: productId });
    refreshCart();
  };

  const handleProductClick = (productId: string) => {
    trackEvent({ event_type: "product_click", session_id: sessionId, product_id: productId });
  };

  const playGame = async () => {
    if (!sessionId || gameLoading) return;
    setGameLoading("spin");
    setGameResult(null);
    setGameModal(null);
    try {
      const result = await playCouponGame(sessionId);
      setGameResult(result);
      setGameModal("spin");
    } catch {
      setGameResult({
        played: true,
        won: false,
        code: null,
        min_order: 50000,
        discount: 1000,
        message: "Something went wrong. Try again later.",
      });
      setGameModal("spin");
    } finally {
      setGameLoading(null);
    }
  };

  const playJackpotGame = async () => {
    if (!sessionId || gameLoading) return;
    setGameLoading("jackpot");
    setGameResultJackpot(null);
    setGameModal(null);
    try {
      const result = await playJackpot(sessionId);
      setGameResultJackpot(result);
      setGameModal("jackpot");
    } catch {
      setGameResultJackpot({
        played: true,
        won: false,
        code: null,
        min_order: 50000,
        discount: 2000,
        message: "Something went wrong. Try again later.",
      });
      setGameModal("jackpot");
    } finally {
      setGameLoading(null);
    }
  };

  const playScratchGame = async () => {
    if (!sessionId || gameLoading) return;
    setGameLoading("scratch");
    setGameResultScratch(null);
    setGameModal(null);
    try {
      const result = await playScratch(sessionId);
      setGameResultScratch(result);
      setGameModal("scratch");
    } catch {
      setGameResultScratch({
        played: true,
        won: false,
        code: null,
        min_order: 50000,
        discount: 500,
        message: "Something went wrong. Try again later.",
      });
      setGameModal("scratch");
    } finally {
      setGameLoading(null);
    }
  };

  const scrollToPicks = () => document.getElementById("recommended-picks")?.scrollIntoView({ behavior: "smooth" });
  const openChat = () => window.dispatchEvent(new CustomEvent("open-aurashop-chat"));

  const recBadges = recommended.map((_, i) => (i === 0 ? "best_match" : i === 1 ? "value" : i === 2 ? "trending" : null));
  const trendBadges = trending.map((_, i) => (i === 0 ? "trending" : null));

  return (
    <div className="space-y-10 sm:space-y-14 py-4 sm:py-6 lg:py-8">
      {/* Hero – compact */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative min-h-[320px] sm:min-h-[360px] rounded-2xl sm:rounded-3xl overflow-hidden"
      >
        <div
          className="absolute inset-0"
          style={{
            background: "linear-gradient(135deg, rgba(49, 46, 129, 0.97) 0%, rgba(88, 28, 135, 0.96) 50%, rgba(30, 58, 138, 0.96) 100%)",
          }}
        />
        <div
          className="absolute inset-0 opacity-20"
          style={{ backgroundImage: `url(${getHeroBackground()})`, backgroundSize: "cover", backgroundPosition: "center" }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
        <div className="relative z-10 h-full flex flex-col justify-center px-5 py-10 sm:p-12 text-white">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 mb-4 bg-black/30 backdrop-blur border border-white/20 text-sm font-semibold w-fit"
          >
            <Sparkles className="h-4 w-4 text-cyan-300" />
            AI-Powered Shopping
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="font-heading text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight mb-2"
          >
            Discover Your Perfect Style
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-white/90 text-sm sm:text-base max-w-lg mb-6"
          >
            Personalized recommendations, deals, and more. Shop by category or ask AI.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="flex flex-wrap gap-3"
          >
            <motion.button
              onClick={openChat}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 rounded-xl bg-white text-indigo-700 px-4 py-2.5 font-semibold shadow-lg hover:bg-gray-50"
            >
              <MessageCircle className="h-4 w-4" />
              Ask AI
            </motion.button>
            <motion.button
              onClick={scrollToPicks}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 rounded-xl bg-black/35 border border-white/30 px-4 py-2.5 font-semibold text-white hover:bg-black/50"
            >
              Explore
              <ChevronDown className="h-4 w-4" />
            </motion.button>
          </motion.div>
        </div>
      </motion.section>

      {/* Shop by category – many options */}
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="scroll-mt-6"
      >
        <h2 className="font-heading text-lg sm:text-xl font-bold text-gray-900 dark:text-white mb-4">
          Shop by category
        </h2>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          {(categories.length > 0 ? categories : FALLBACK_CATEGORIES).map((cat, i) => {
            const Icon = getCategoryIcon(cat);
            return (
              <Link key={cat} href={`/products?category=${encodeURIComponent(cat)}`}>
                <motion.span
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.02 }}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.98 }}
                  className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 hover:text-indigo-700 dark:hover:text-indigo-300 shadow-sm transition-all"
                >
                  <Icon className="h-4 w-4 text-indigo-500 shrink-0" />
                  {cat}
                </motion.span>
              </Link>
            );
          })}
        </div>
      </motion.section>

      {/* Recommended for you */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="aspect-[3/4] sm:h-72 rounded-2xl bg-gray-200 dark:bg-gray-800 animate-pulse" />
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

          {/* Games – Play & Win: Spin Wheel, Jackpot, Lucky Scratch */}
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative overflow-hidden rounded-2xl sm:rounded-3xl border-2 border-amber-300/60 dark:border-amber-600/40 bg-gradient-to-br from-amber-100 via-orange-50 to-amber-100 dark:from-amber-950/50 dark:via-orange-950/30 dark:to-amber-950/50 p-6 sm:p-8 shadow-xl shadow-amber-500/10"
          >
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(251,191,36,0.15),transparent)] pointer-events-none" />
            <div className="absolute top-0 right-0 w-64 h-64 bg-amber-400/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
            <div className="relative flex items-center gap-4 mb-6">
              <motion.div
                className="h-14 w-14 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/30"
                whileHover={{ scale: 1.05, rotate: 5 }}
                transition={{ type: "spring", stiffness: 400 }}
              >
                <Gift className="h-7 w-7 text-white" />
              </motion.div>
              <div>
                <h2 className="font-heading text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  Play & Win
                  <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-800 dark:text-amber-200">₹50k+ orders</span>
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                  Spin, jackpot, or scratch — one play per game. Win coupons for orders above ₹50,000.
                </p>
              </div>
            </div>
            <div className="relative grid sm:grid-cols-3 gap-5">
              {/* Spin Wheel card – with mini wheel visual */}
              <motion.div
                className="group relative rounded-2xl border-2 border-amber-300/70 dark:border-amber-600/50 bg-white/90 dark:bg-gray-900/70 backdrop-blur p-5 shadow-lg hover:shadow-xl hover:shadow-amber-500/15 transition-all overflow-hidden"
                whileHover={{ y: -4, scale: 1.02 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <div className="absolute top-2 right-2 w-20 h-20 rounded-full opacity-20 group-hover:opacity-30 transition-opacity pointer-events-none" style={{ background: "conic-gradient(#fde68a 0deg 120deg, #e5e7eb 120deg 240deg, #fde68a 240deg 360deg)" }} />
                <div className="relative flex items-center gap-3 mb-3">
                  <motion.div
                    className="h-10 w-10 rounded-xl bg-amber-500/20 flex items-center justify-center border border-amber-400/40"
                    animate={{ rotate: gameLoading === "spin" ? 360 : 0 }}
                    transition={{ duration: 1, repeat: gameLoading === "spin" ? Infinity : 0, ease: "linear" }}
                  >
                    <Ticket className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </motion.div>
                  <div>
                    <span className="font-bold text-gray-900 dark:text-white">Spin Wheel</span>
                    <p className="text-xs text-amber-700 dark:text-amber-300 font-medium">₹1,000 off</p>
                  </div>
                </div>
                {!gameResult ? (
                  <motion.button
                    onClick={playGame}
                    disabled={!!gameLoading}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 disabled:opacity-60 text-white font-semibold px-4 py-3 text-sm shadow-md"
                  >
                    {gameLoading === "spin" ? "Opening wheel…" : "Spin the wheel"}
                  </motion.button>
                ) : (
                  <div className={`rounded-xl p-3 text-sm border ${gameResult.won ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800" : "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700"}`}>
                    <p className="font-semibold text-gray-900 dark:text-white">{gameResult.won ? "🎉 Won!" : "Better luck"}</p>
                    {gameResult.won && gameResult.code && (
                      <p className="font-mono text-emerald-700 dark:text-emerald-400 mt-1 text-xs">{gameResult.code}</p>
                    )}
                  </div>
                )}
              </motion.div>
              {/* Jackpot card */}
              <motion.div
                className="group relative rounded-2xl border-2 border-amber-300/70 dark:border-amber-600/50 bg-white/90 dark:bg-gray-900/70 backdrop-blur p-5 shadow-lg hover:shadow-xl hover:shadow-amber-500/15 transition-all overflow-hidden"
                whileHover={{ y: -4, scale: 1.02 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <div className="absolute top-2 right-2 text-2xl opacity-20 group-hover:opacity-30 transition-opacity">7 ★ 🍒</div>
                <div className="relative flex items-center gap-3 mb-3">
                  <motion.div className="h-10 w-10 rounded-xl bg-amber-600/20 flex items-center justify-center border border-amber-500/40" whileHover={{ scale: 1.1 }}>
                    <Trophy className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </motion.div>
                  <div>
                    <span className="font-bold text-gray-900 dark:text-white">Jackpot</span>
                    <p className="text-xs text-amber-700 dark:text-amber-300 font-medium">₹2,000 off</p>
                  </div>
                </div>
                {!gameResultJackpot ? (
                  <motion.button
                    onClick={playJackpotGame}
                    disabled={!!gameLoading}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 disabled:opacity-60 text-white font-semibold px-4 py-3 text-sm shadow-md"
                  >
                    {gameLoading === "jackpot" ? "Spinning reels…" : "Play Jackpot"}
                  </motion.button>
                ) : (
                  <div className={`rounded-xl p-3 text-sm border ${gameResultJackpot.won ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800" : "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700"}`}>
                    <p className="font-semibold text-gray-900 dark:text-white">{gameResultJackpot.won ? "🎉 Jackpot!" : "Better luck"}</p>
                    {gameResultJackpot.won && gameResultJackpot.code && (
                      <p className="font-mono text-emerald-700 dark:text-emerald-400 mt-1 text-xs">{gameResultJackpot.code}</p>
                    )}
                  </div>
                )}
              </motion.div>
              {/* Lucky Scratch card */}
              <motion.div
                className="group relative rounded-2xl border-2 border-amber-300/70 dark:border-amber-600/50 bg-white/90 dark:bg-gray-900/70 backdrop-blur p-5 shadow-lg hover:shadow-xl hover:shadow-amber-500/15 transition-all overflow-hidden"
                whileHover={{ y: -4, scale: 1.02 }}
                transition={{ type: "spring", stiffness: 300 }}
              >
                <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: "repeating-linear-gradient(45deg, #000 0, #000 1px, transparent 1px, transparent 8px)" }} />
                <div className="relative flex items-center gap-3 mb-3">
                  <motion.div className="h-10 w-10 rounded-xl bg-amber-500/20 flex items-center justify-center border border-amber-400/40" whileHover={{ scale: 1.1 }}>
                    <Scissors className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                  </motion.div>
                  <div>
                    <span className="font-bold text-gray-900 dark:text-white">Lucky Scratch</span>
                    <p className="text-xs text-amber-700 dark:text-amber-300 font-medium">₹500 off</p>
                  </div>
                </div>
                {!gameResultScratch ? (
                  <motion.button
                    onClick={playScratchGame}
                    disabled={!!gameLoading}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 disabled:opacity-60 text-white font-semibold px-4 py-3 text-sm shadow-md"
                  >
                    {gameLoading === "scratch" ? "Opening card…" : "Scratch to win"}
                  </motion.button>
                ) : (
                  <div className={`rounded-xl p-3 text-sm border ${gameResultScratch.won ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800" : "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700"}`}>
                    <p className="font-semibold text-gray-900 dark:text-white">{gameResultScratch.won ? "🎉 Won!" : "Better luck"}</p>
                    {gameResultScratch.won && gameResultScratch.code && (
                      <p className="font-mono text-emerald-700 dark:text-emerald-400 mt-1 text-xs">{gameResultScratch.code}</p>
                    )}
                  </div>
                )}
              </motion.div>
            </div>
          </motion.section>

          {/* Trending now */}
          <ProductCarousel
            title="🔥 Trending Now"
            products={trending}
            badges={trendBadges}
            sessionId={sessionId}
            onAddToCart={handleAddToCart}
            onProductClick={handleProductClick}
          />

          {/* Premium picks – products above ₹50k (use with coupon) */}
          {(premium.length > 0 || !loading) && (
            <ProductCarousel
              title="💎 Premium Picks (₹50k+) — Use your coupon here"
              products={premium}
              sessionId={sessionId}
              onAddToCart={handleAddToCart}
              onProductClick={handleProductClick}
            />
          )}

          {/* Category carousels */}
          {Object.entries(categoryProducts).map(
            ([cat, prods]) =>
              prods.length > 0 && (
                <ProductCarousel
                  key={cat}
                  title={cat}
                  products={prods}
                  sessionId={sessionId}
                  onAddToCart={handleAddToCart}
                  onProductClick={handleProductClick}
                />
              )
          )}

          {/* Your orders */}
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-heading text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <PackageCheck className="h-5 w-5 text-indigo-500" />
                Your orders
              </h2>
              <Link
                href="/profile"
                className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
              >
                See all
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
            {orders.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No orders yet. Start shopping!</p>
            ) : (
              <ul className="space-y-3">
                {orders.map((order) => (
                  <li key={order.id}>
                    <Link
                      href={`/orders/${order.id}`}
                      className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 p-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <span className="font-medium text-gray-900 dark:text-white">Order {order.id}</span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {formatPrice(order.total)} · {order.status}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </motion.section>

          {/* Returns */}
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  <RotateCcw className="h-6 w-6 text-indigo-500" />
                </div>
                <div>
                  <h2 className="font-heading text-lg font-bold text-gray-900 dark:text-white">
                    Returns & replacements
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Start a return or check our return policy
                  </p>
                </div>
              </div>
              <Link
                href="/profile"
                className="rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 px-4 py-2.5 text-sm font-semibold text-gray-900 dark:text-white transition-colors flex items-center gap-1"
              >
                Go to orders
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          </motion.section>
        </>
      )}

      {/* Game modals with real animations */}
      <AnimatePresence>
        {gameModal === "spin" && gameResult && (
          <HomeSpinWheel
            won={gameResult.won}
            discount={gameResult.discount}
            code={gameResult.code}
            message={gameResult.message}
            minOrder={gameResult.min_order}
            onClose={() => setGameModal(null)}
          />
        )}
        {gameModal === "jackpot" && gameResultJackpot && (
          <HomeJackpot
            won={gameResultJackpot.won}
            discount={gameResultJackpot.discount}
            code={gameResultJackpot.code}
            message={gameResultJackpot.message}
            minOrder={gameResultJackpot.min_order}
            onClose={() => setGameModal(null)}
          />
        )}
        {gameModal === "scratch" && gameResultScratch && (
          <HomeScratch
            won={gameResultScratch.won}
            discount={gameResultScratch.discount}
            code={gameResultScratch.code}
            message={gameResultScratch.message}
            minOrder={gameResultScratch.min_order}
            onClose={() => setGameModal(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
