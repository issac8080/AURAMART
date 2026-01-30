"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { Star, ShoppingCart, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProductCard } from "@/components/ProductCard";
import { useCart } from "@/app/providers";
import { fetchProduct, fetchRecommendations, trackEvent } from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import { getProductImageSrc, getProductImagePlaceholder } from "@/lib/unsplash";
import type { Product } from "@/lib/api";

export default function ProductDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const { sessionId, refreshCart } = useCart();
  const [product, setProduct] = useState<Product | null>(null);
  const [similar, setSimilar] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    trackEvent({
      event_type: "product_click",
      session_id: sessionId,
      product_id: id,
    });
    trackEvent({
      event_type: "page_view",
      session_id: sessionId,
      product_id: id,
      metadata: { page: "product_detail" },
    });
  }, [id, sessionId]);

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      try {
        const [p, recRes] = await Promise.all([
          fetchProduct(id),
          fetchRecommendations(sessionId, { limit: 4, exclude_product_ids: id }),
        ]);
        setProduct(p);
        const similarProducts = recRes.recommendations
          .map((r) => (r.product ? { ...r.product, id: r.product_id } as Product : null))
          .filter(Boolean) as Product[];
        setSimilar(similarProducts);
      } catch {
        setProduct(null);
        setSimilar([]);
      } finally {
        setLoading(false);
      }
    }
    if (sessionId && id) load();
  }, [id, sessionId]);

  const handleAddToCart = (productId: string) => {
    trackEvent({ event_type: "cart_add", session_id: sessionId, product_id: productId });
    refreshCart();
  };

  const handleProductClick = (productId: string) => {
    trackEvent({ event_type: "product_click", session_id: sessionId, product_id: productId });
  };

  if (loading && !product) {
    return (
      <div className="py-8 animate-pulse space-y-6">
        <div className="h-8 w-48 bg-muted rounded" />
        <div className="grid md:grid-cols-2 gap-8">
          <div className="aspect-square bg-muted rounded-xl" />
          <div className="space-y-4">
            <div className="h-8 bg-muted rounded w-3/4" />
            <div className="h-4 bg-muted rounded w-1/2" />
            <div className="h-24 bg-muted rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">Product not found.</p>
        <Link href="/products">
          <Button variant="outline" className="mt-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to products
          </Button>
        </Link>
      </div>
    );
  }

  const whyRight = [
    product.rating >= 4.5 && "Highly rated by buyers",
    product.review_count > 100 && "Popular choice",
    product.in_stock && product.stock_count != null && product.stock_count <= 10 && "Only a few left",
    product.price < 2000 && "Great value for money",
  ].filter(Boolean);

  return (
    <div className="py-6 space-y-8">
      <Link href="/products" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" />
        Back to products
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid md:grid-cols-2 gap-8"
      >
        <div className="aspect-square rounded-xl bg-muted overflow-hidden relative">
          <img
            src={getProductImageSrc(product.image_url, product.category, product.id, product.name)}
            alt={product.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.src = getProductImagePlaceholder(product.name);
            }}
          />
        </div>

        <div className="space-y-4">
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">{product.name}</h1>
          <p className="text-muted-foreground">{product.category}</p>
          <div className="flex items-center gap-2">
            <Star className="h-5 w-5 fill-amber-400 text-amber-400" />
            <span className="font-medium">{product.rating}</span>
            <span className="text-muted-foreground">({product.review_count} reviews)</span>
          </div>
          <p className="font-heading text-fluid-2xl sm:text-fluid-3xl font-bold text-primary">{formatPrice(product.price)}</p>
          <p className="text-muted-foreground">{product.description}</p>
          {product.colors?.length ? (
            <div>
              <span className="text-sm font-medium">Colors: </span>
              <span className="text-sm text-muted-foreground">{product.colors.join(", ")}</span>
            </div>
          ) : null}
          {product.sizes?.length ? (
            <div>
              <span className="text-sm font-medium">Sizes: </span>
              <span className="text-sm text-muted-foreground">{product.sizes.join(", ")}</span>
            </div>
          ) : null}
          {product.stock_count != null && product.stock_count <= 10 && (
            <p className="text-amber-600 dark:text-amber-400 text-sm font-medium">
              Only {product.stock_count} left in stock
            </p>
          )}
          <Button
            size="lg"
            className="w-full sm:w-auto"
            onClick={() => {
              trackEvent({ event_type: "cart_add", session_id: sessionId, product_id: product.id });
              refreshCart();
            }}
          >
            <ShoppingCart className="h-5 w-5 mr-2" />
            Add to cart
          </Button>
        </div>
      </motion.div>

      {whyRight.length > 0 && (
        <Card className="border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 glass-card">
          <CardContent className="p-4">
            <h2 className="font-heading font-bold text-primary mb-2 flex items-center gap-2"><Sparkles className="h-4 w-4" /> Why this product is right for you</h2>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              {whyRight.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {similar.length > 0 && (
        <section>
          <h2 className="font-heading text-fluid-lg font-bold mb-4">Similar & alternatives</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {similar.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                sessionId={sessionId}
                onAddToCart={handleAddToCart}
                trackClick={handleProductClick}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
