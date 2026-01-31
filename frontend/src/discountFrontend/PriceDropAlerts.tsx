"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchPriceDropNotifications } from "./api";
import type { PriceDropNotification } from "./types";
import { TrendingDown, ExternalLink, Info } from "lucide-react";
import { useCart } from "@/app/providers";
import { getProductImageUrl } from "@/lib/unsplash";

/** Example price drops shown when user has no real notifications (for demo) */
const EXAMPLE_PRICE_DROPS: PriceDropNotification[] = [
  {
    product_id: "P00001",
    product_name: "Alisha Solid Women's Cycling Shorts",
    old_price: 379,
    new_price: 299,
    percent_off: 21.1,
    image_url: "https://picsum.photos/seed/P00001/200/200",
  },
  {
    product_id: "P00003",
    product_name: "AW Bellies Sandals",
    old_price: 499,
    new_price: 399,
    percent_off: 20.0,
    image_url: "https://picsum.photos/seed/P00003/200/200",
  },
  {
    product_id: "P00002",
    product_name: "FabHomeDecor Fabric Double Sofa Bed",
    old_price: 22646,
    new_price: 19999,
    percent_off: 11.7,
    image_url: "https://picsum.photos/seed/P00002/200/200",
  },
];

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

  const displayItems = notifications.length > 0 ? notifications : EXAMPLE_PRICE_DROPS;
  const isExample = notifications.length === 0 && !loading;

  if (loading && notifications.length === 0) return null;
  if (displayItems.length === 0) return null;

  return (
    <Card className="border-teal-200 dark:border-teal-800 bg-teal-50/50 dark:bg-teal-950/30">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2 text-teal-700 dark:text-teal-400">
          <TrendingDown className="h-5 w-5" />
          <h3 className="font-semibold">Price dropped on items you viewed</h3>
        </div>
        {isExample && (
          <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
            <Info className="h-3.5 w-3.5" />
            Example — view products to get real price drop alerts when prices go down
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {displayItems.map((n) => (
          <div
            key={n.product_id}
            className="flex items-center gap-3 rounded-lg border border-teal-200/50 dark:border-teal-800/50 bg-white dark:bg-teal-900/20 p-3"
          >
            {(n.image_url || n.product_id) && (
              <img
                src={getProductImageUrl(n.image_url, "", n.product_id)}
                alt=""
                className="h-12 w-12 rounded object-cover flex-shrink-0"
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
