"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fetchFestivals } from "./api";
import type { Festival } from "./types";
import { Calendar, ChevronRight } from "lucide-react";

function isActive(f: Festival): boolean {
  const now = new Date().toISOString();
  return f.start <= now && now <= f.end;
}

export function FestivalBanner() {
  const [festivals, setFestivals] = useState<Festival[]>([]);

  useEffect(() => {
    fetchFestivals()
      .then((data) => setFestivals(data.festivals || []))
      .catch(() => setFestivals([]));
  }, []);

  const active = festivals.filter(isActive);
  if (active.length === 0) return null;

  return (
    <Card className="overflow-hidden border-rose-200 dark:border-rose-800 bg-gradient-to-r from-rose-50 to-amber-50 dark:from-rose-950/40 dark:to-amber-950/30">
      <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-rose-500/20 p-2">
            <Calendar className="h-5 w-5 text-rose-600 dark:text-rose-400" />
          </div>
          <div>
            <p className="font-semibold text-rose-800 dark:text-rose-300">
              {active[0].label}
            </p>
            <p className="text-sm text-muted-foreground">
              {active[0].percent}% off storewide — limited time
            </p>
          </div>
        </div>
        <Button asChild variant="default" size="sm">
          <Link href="/discountFrontend">
            See all offers <ChevronRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
