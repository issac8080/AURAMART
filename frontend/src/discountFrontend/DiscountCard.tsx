"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AppliedDiscount } from "./types";
import { Tag, Percent, Gift, Sparkles, Store, Calendar, CreditCard } from "lucide-react";

const typeIcons: Record<string, React.ReactNode> = {
  new_user: <Gift className="h-4 w-4" />,
  loyal_customer: <Sparkles className="h-4 w-4" />,
  vendor: <Store className="h-4 w-4" />,
  festival: <Calendar className="h-4 w-4" />,
  subscription: <CreditCard className="h-4 w-4" />,
  price_drop: <Percent className="h-4 w-4" />,
};

const typeColors: Record<string, string> = {
  new_user: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  loyal_customer: "bg-violet-500/15 text-violet-700 dark:text-violet-400",
  vendor: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  festival: "bg-rose-500/15 text-rose-700 dark:text-rose-400",
  subscription: "bg-blue-500/15 text-blue-700 dark:text-blue-400",
  price_drop: "bg-teal-500/15 text-teal-700 dark:text-teal-400",
};

export function DiscountCard({ discount }: { discount: AppliedDiscount }) {
  const icon = typeIcons[discount.discount_type] ?? <Tag className="h-4 w-4" />;
  const color = typeColors[discount.discount_type] ?? "bg-muted text-muted-foreground";

  return (
    <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-card to-primary/5">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <Badge className={`gap-1 ${color}`} variant="secondary">
            {icon}
            <span className="capitalize">{discount.discount_type.replace("_", " ")}</span>
          </Badge>
          <span className="text-lg font-bold text-primary">
            {discount.percent > 0 ? `${discount.percent}% off` : ""}
            {discount.amount > 0 ? ` −₹${discount.amount.toFixed(0)}` : ""}
          </span>
        </div>
        <h3 className="font-semibold">{discount.label}</h3>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="text-sm text-muted-foreground">{discount.description}</p>
      </CardContent>
    </Card>
  );
}
