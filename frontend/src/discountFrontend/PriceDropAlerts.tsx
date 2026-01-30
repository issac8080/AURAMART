"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchPriceDropNotifications } from "./api";
import type { PriceDropNotification } from "./types";
import { TrendingDown, ExternalLink } from "lucide-react";
import { useCart } from "@/app/providers";

type PriceDropAlertsProps = {
  sessionIdOverride?: string | null;
  userIdOverride?: string | null;
};

export function PriceDropAlerts({ sessionIdOverride, userIdOverride }: PriceDropAlertsProps = {}) {
  const { sessionId } = useCart();
  const effectiveSessionId = sessionIdOverride ?? sessionId;
  const [notifications, setNotifications] = useState<PriceDropNotification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!effectiveSessionId) {
      setLoading(false);
      return;
    }
    fetchPriceDropNotifications(effectiveSessionId, userIdOverride ?? undefined)
      .then((data) => setNotifications(data.notifications || []))
      .catch(() => setNotifications([]))
      .finally(() => setLoading(false));
  }, [effectiveSessionId, userIdOverride]);

  if (loading || notifications.length === 0) return null;

  return (
    <Card className="border-teal-200 dark:border-teal-800 bg-teal-50/50 dark:bg-teal-950/30">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2 text-teal-700 dark:text-teal-400">
          <TrendingDown className="h-5 w-5" />
          <h3 className="font-semibold">Price dropped on items you viewed</h3>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {notifications.map((n) => (
          <div
            key={n.product_id}
            className="flex items-center gap-3 rounded-lg border border-teal-200/50 dark:border-teal-800/50 bg-white dark:bg-teal-900/20 p-3"
          >
            {n.image_url && (
              <img
                src={n.image_url}
                alt=""
                className="h-12 w-12 rounded object-cover"
              />
            )}
            <div className="min-w-0 flex-1">
              <p className="font-medium truncate">{n.product_name}</p>
              <p className="text-sm text-muted-foreground">
                ₹{n.old_price.toLocaleString()} → ₹{n.new_price.toLocaleString()}{" "}
                <span className="font-medium text-teal-600 dark:text-teal-400">
                  ({n.percent_off}% off)
                </span>
              </p>
            </div>
            <Button asChild size="sm" variant="outline">
              <Link href={`/products/${n.product_id}`}>
                View <ExternalLink className="ml-1 h-3 w-3" />
              </Link>
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
