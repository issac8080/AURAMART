"use client";

import { useRef, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProductCard } from "./ProductCard";
import type { Product } from "@/lib/api";

export function ProductCarousel({
  title,
  products,
  badges,
  sessionId,
  onAddToCart,
  onProductClick,
}: {
  title: string;
  products: Product[];
  badges?: ("best_match" | "value" | "trending" | null)[];
  sessionId?: string;
  onAddToCart?: (productId: string) => void;
  onProductClick?: (productId: string) => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (dir: "left" | "right") => {
    if (!scrollRef.current) return;
    const step = scrollRef.current.clientWidth * 0.8;
    scrollRef.current.scrollBy({ left: dir === "left" ? -step : step, behavior: "smooth" });
  };

  if (!products.length) return null;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-heading text-lg sm:text-xl font-bold tracking-tight text-foreground">
          {title}
        </h2>
        <div className="flex gap-2 shrink-0">
          <Button variant="outline" size="icon" className="h-10 w-10 rounded-2xl border-border/80 hover:border-primary/30 hover:shadow-glow transition-all" onClick={() => scroll("left")} aria-label="Scroll left">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" className="h-10 w-10 rounded-2xl border-border/80 hover:border-primary/30 hover:shadow-glow transition-all" onClick={() => scroll("right")} aria-label="Scroll right">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div
        ref={scrollRef}
        className="flex gap-4 overflow-x-auto scroll-smooth pb-2 -mx-1 px-1 snap-x snap-mandatory scrollbar-hide"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {products.map((product, i) => (
          <div
            key={product.id}
            className="flex-shrink-0 w-[180px] sm:w-[220px] snap-start"
          >
            <ProductCard
              product={product}
              badge={badges?.[i] ?? null}
              sessionId={sessionId}
              onAddToCart={onAddToCart}
              trackClick={onProductClick}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
