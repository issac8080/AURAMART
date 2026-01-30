"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Tag,
  Gift,
  TrendingDown,
  Sparkles,
  Store,
  Calendar,
  CreditCard,
  ShoppingCart,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  fetchApplicableDiscounts,
  fetchPriceDropNotifications,
  fetchSubscriptionTiers,
  fetchFestivals,
} from "@/discountFrontend/api";
import { DiscountCard as DiscountCardComponent } from "@/discountFrontend/DiscountCard";
import { PriceDropAlerts } from "@/discountFrontend/PriceDropAlerts";
import { SubscriptionSection } from "@/discountFrontend/SubscriptionSection";
import { SubscriptionCard } from "@/discountFrontend/SubscriptionCard";
import { FestivalBanner } from "@/discountFrontend/FestivalBanner";
import type { AppliedDiscount, Festival } from "@/discountFrontend/types";
import { useCart } from "@/app/providers";

const discountTypeLabels: Record<string, { label: string; icon: React.ReactNode }> = {
  new_user: { label: "New user discount", icon: <Gift className="h-4 w-4" /> },
  price_drop: { label: "Price drop alerts", icon: <TrendingDown className="h-4 w-4" /> },
  loyal_customer: { label: "Loyal customer", icon: <Sparkles className="h-4 w-4" /> },
  vendor: { label: "Vendor offers", icon: <Store className="h-4 w-4" /> },
  festival: { label: "Festival discounts", icon: <Calendar className="h-4 w-4" /> },
  subscription: { label: "Subscription discount", icon: <CreditCard className="h-4 w-4" /> },
};

export default function DiscountFrontendPage() {
  const { sessionId } = useCart();
  const [discounts, setDiscounts] = useState<AppliedDiscount[]>([]);
  const [festivals, setFestivals] = useState<Festival[]>([]);
  const [orderTotal, setOrderTotal] = useState(1000);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }
    const userId = sessionId;
    fetchApplicableDiscounts(userId, sessionId, orderTotal, [])
      .then((data) => setDiscounts(data.discounts || []))
      .catch(() => setDiscounts([]))
      .finally(() => setLoading(false));

    fetchFestivals()
      .then((data) => setFestivals(data.festivals || []))
      .catch(() => setFestivals([]));
  }, [sessionId, orderTotal]);

  return (
    <div className="py-8 space-y-8">
      <div className="flex items-center gap-4">
        <Button asChild variant="ghost" size="icon">
          <Link href="/">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Tag className="h-7 w-7 text-primary" />
            Discounts & Offers
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            New user, loyalty, festival, vendor & subscription discounts
          </p>
        </div>
      </div>

      <FestivalBanner />

      <section>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <TrendingDown className="h-5 w-5 text-teal-500" />
          Price drop on items you viewed
        </h2>
        <PriceDropAlerts />
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-blue-500" />
          Aura Subscription — ₹50/month
        </h2>
        <SubscriptionCard />
        <div className="mt-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">All plans</h3>
          <SubscriptionSection />
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Your applicable discounts</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Based on your cart total (simulated ₹{orderTotal}). Change in checkout.
        </p>
        {loading ? (
          <p className="text-muted-foreground">Loading…</p>
        ) : discounts.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              <Tag className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No discounts applicable right now.</p>
              <p className="text-sm mt-1">
                Add items to cart and complete more orders to unlock loyalty & more.
              </p>
              <Button asChild variant="outline" className="mt-4">
                <Link href="/products">Browse products</Link>
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {discounts.map((d) => (
              <motion.div
                key={`${d.discount_type}-${d.product_id ?? ""}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                <DiscountCardComponent discount={d} />
              </motion.div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">All discount types</h2>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(discountTypeLabels).map(([type, { label, icon }]) => (
            <Card key={type} className="p-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                {icon}
                <span className="text-sm font-medium capitalize">
                  {label}
                </span>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <div className="flex justify-center">
        <Button asChild>
          <Link href="/checkout" className="inline-flex items-center gap-2">
            <ShoppingCart className="h-4 w-4" />
            Go to checkout
          </Link>
        </Button>
      </div>
    </div>
  );
}
