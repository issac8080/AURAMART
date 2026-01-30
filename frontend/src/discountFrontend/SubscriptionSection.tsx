"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  fetchSubscriptionTiers,
  setUserSubscription,
} from "./api";
import type { SubscriptionTier } from "./types";
import { CreditCard, Check } from "lucide-react";
import { useCart } from "@/app/providers";

export function SubscriptionSection() {
  const { sessionId } = useCart();
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [activeTierId, setActiveTierId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubscriptionTiers()
      .then((data) => setTiers(data.tiers || []))
      .catch(() => setTiers([]))
      .finally(() => setLoading(false));
  }, []);

  const handleSubscribe = async (tierId: string) => {
    if (!sessionId) return;
    try {
      await setUserSubscription(sessionId, tierId);
      setActiveTierId(tierId);
    } catch (e) {
      console.error(e);
    }
  };

  const handleUnsubscribe = async () => {
    if (!sessionId) return;
    try {
      await setUserSubscription(sessionId, null);
      setActiveTierId(null);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading || tiers.length === 0) return null;

  return (
    <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/30">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400">
          <CreditCard className="h-5 w-5" />
          <h3 className="font-semibold">Subscription discounts</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Get extra % off on every order with a plan.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {tiers.map((tier) => {
          const isActive = activeTierId === tier.id;
          return (
            <div
              key={tier.id}
              className={`flex items-center justify-between rounded-lg border p-3 ${
                isActive
                  ? "border-primary bg-primary/10"
                  : "border-border bg-card"
              }`}
            >
              <div>
                <p className="font-medium">{tier.name}</p>
                <p className="text-sm text-muted-foreground">
                  {tier.discount_percent}% off all orders · ₹{tier.monthly_price}/mo
                </p>
              </div>
              <Button
                size="sm"
                variant={isActive ? "secondary" : "default"}
                onClick={() =>
                  isActive ? handleUnsubscribe() : handleSubscribe(tier.id)
                }
              >
                {isActive ? (
                  <>
                    <Check className="mr-1 h-4 w-4" /> Active
                  </>
                ) : (
                  "Subscribe"
                )}
              </Button>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
