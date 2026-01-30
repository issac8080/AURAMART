"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { Star, ShoppingCart, Sparkles } from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { formatPrice } from "@/lib/utils";
import { getProductImage } from "@/lib/unsplash";
import type { Product } from "@/lib/api";

type BadgeType = "best_match" | "value" | "trending" | null;

const BADGE_CONFIG: Record<NonNullable<BadgeType>, { label: string; className: string; why: string }> = {
  best_match: { label: "Best Match", className: "pill-ai-best", why: "AI picked for your taste" },
  value: { label: "Value", className: "pill-ai-value", why: "Great value for money" },
  trending: { label: "Trending", className: "pill-ai-trending", why: "Trending now" },
};

export function ProductCard({
  product,
  badge = null,
  onAddToCart,
  sessionId,
  trackClick,
}: {
  product: Product;
  badge?: BadgeType;
  onAddToCart?: (productId: string) => void;
  sessionId?: string;
  trackClick?: (productId: string) => void;
}) {
  const handleClick = () => {
    trackClick?.(product.id);
  };

  const badgeConfig = badge ? BADGE_CONFIG[badge] : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="h-full"
    >
      <Card className="overflow-hidden group h-full flex flex-col rounded-2xl sm:rounded-3xl border border-border/80 bg-card shadow-card hover:shadow-card-hover hover:border-primary/25 transition-all duration-300">
        <Link href={`/products/${product.id}`} onClick={handleClick} className="block">
          <div className="aspect-square bg-muted/50 relative overflow-hidden">
            <Image
              src={getProductImage(product.category, product.id)}
              alt={product.name}
              fill
              unoptimized
              className="object-cover group-hover:scale-110 transition-transform duration-500 ease-out"
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            />
            {badgeConfig && (
              <span
                title={badgeConfig.why}
                className={cn(
                  "absolute top-3 left-3 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold text-white shadow-lg",
                  badgeConfig.className
                )}
              >
                <Sparkles className="h-3 w-3" />
                {badgeConfig.label}
              </span>
            )}
          </div>
        </Link>
        <CardContent className="p-3.5 sm:p-4 flex-1 flex flex-col min-w-0">
          <Link href={`/products/${product.id}`} onClick={handleClick}>
            <p className="font-semibold text-sm sm:text-base line-clamp-2 group-hover:text-primary transition-colors leading-snug">
              {product.name}
            </p>
          </Link>
          <p className="text-muted-foreground text-xs mt-0.5 truncate">{product.category}</p>
          <div className="flex items-center gap-1.5 mt-2">
            <Star className="h-4 w-4 fill-amber-400 text-amber-400 shrink-0" />
            <span className="text-xs font-semibold">{product.rating}</span>
            <span className="text-xs text-muted-foreground">({product.review_count})</span>
          </div>
          <p className="font-bold text-primary text-lg mt-2">{formatPrice(product.price)}</p>
        </CardContent>
        <CardFooter className="p-3.5 sm:p-4 pt-0">
          <Button
            size="sm"
            className="w-full rounded-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 shadow-lg shadow-primary/25"
            onClick={(e) => {
              e.preventDefault();
              onAddToCart?.(product.id);
            }}
          >
            <ShoppingCart className="h-4 w-4 mr-2" />
            Add to cart
          </Button>
        </CardFooter>
      </Card>
    </motion.div>
  );
}
