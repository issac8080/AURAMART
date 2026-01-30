"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  fetchSubscriptionTiers,
  setUserSubscription,
} from "./api";
import type { SubscriptionTier } from "./types";
import {
  CreditCard,
  Sparkles,
  Check,
  ChevronRight,
} from "lucide-react";
import { useCart } from "@/app/providers";

const STARTER_BENEFITS = [
  "5% off on every order",
  "Free delivery on orders above ₹499",
  "Early access to flash sales",
  "Exclusive member-only deals",
  "Price drop alerts on saved items",
  "Cancel anytime",
];

const DEFAULT_STARTER_TIER: SubscriptionTier = {
  id: "starter",
  name: "Aura Starter",
  discount_percent: 5,
  monthly_price: 50,
};

export function SubscriptionCard() {
  const { sessionId } = useCart();
  const [tier, setTier] = useState<SubscriptionTier>(DEFAULT_STARTER_TIER);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchSubscriptionTiers()
      .then((data) => {
        const tiers = data.tiers || [];
        const starter = tiers.find(
          (t) => t.monthly_price === 50 || t.id === "starter"
        );
        if (starter) setTier(starter);
        else if (tiers[0]) setTier(tiers[0]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSubscribe = async () => {
    if (!sessionId || !tier) return;
    setSubmitting(true);
    try {
      await setUserSubscription(sessionId, tier.id);
      setIsSubscribed(true);
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  const price = tier.monthly_price;
  const isStarter = price === 50 || tier.id === "starter";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card className="overflow-hidden border-2 border-primary/30 bg-gradient-to-br from-primary/5 via-card to-primary/10 dark:from-primary/10 dark:to-primary/5">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-primary/20 p-3">
                <CreditCard className="h-8 w-8 text-primary" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold">{tier.name}</h2>
                  {isStarter && (
                    <Badge variant="secondary" className="bg-amber-500/20 text-amber-700 dark:text-amber-400">
                      Popular
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mt-0.5">
                  {tier.discount_percent}% off on all orders
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-primary">₹{price}</p>
              <p className="text-xs text-muted-foreground">per month</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <p className="text-sm font-medium mb-2 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Benefits
            </p>
            <ul className="space-y-2">
              {STARTER_BENEFITS.map((benefit, i) => (
                <li
                  key={i}
                  className="flex items-center gap-2 text-sm text-muted-foreground"
                >
                  <Check className="h-4 w-4 shrink-0 text-emerald-500" />
                  {benefit}
                </li>
              ))}
            </ul>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            {isSubscribed ? (
              <Button variant="secondary" className="flex-1" asChild>
                <Link href="/discountFrontend">
                  Manage subscription <ChevronRight className="ml-1 h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <>
                <Button
                  className="flex-1"
                  onClick={handleSubscribe}
                  disabled={submitting || !sessionId}
                >
                  {submitting ? "Subscribing…" : `Subscribe for ₹${price}/mo`}
                </Button>
                <Button variant="outline" asChild>
                  <Link href="/discountFrontend">
                    View all plans <ChevronRight className="ml-1 h-4 w-4" />
                  </Link>
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
