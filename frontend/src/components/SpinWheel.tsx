"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Gift, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SEGMENTS = ["Better luck", "1 Pt", "2 Pts", "2 Pts", "3 Pts", "10 Pts"];
const SEGMENT_DEG = 360 / SEGMENTS.length;
const SEGMENT_COLORS = [
  "bg-gray-200 dark:bg-gray-700",
  "bg-amber-200 dark:bg-amber-800",
  "bg-emerald-200 dark:bg-emerald-800",
  "bg-emerald-300 dark:bg-emerald-700",
  "bg-blue-200 dark:bg-blue-800",
  "bg-amber-400 dark:bg-amber-600",
];
const SEGMENT_HEX = ["#e5e7eb", "#fde68a", "#a7f3d0", "#6ee7b7", "#bfdbfe", "#fbbf24"];
const conicGradient = `conic-gradient(${SEGMENT_HEX.map((c, i) => `${c} ${i * SEGMENT_DEG}deg ${(i + 1) * SEGMENT_DEG}deg`).join(", ")})`;

function pointsToSegmentIndex(points: number): number {
  if (points === 0) return 0;
  if (points === 1) return 1;
  if (points === 2) return Math.random() < 0.5 ? 2 : 3;
  if (points === 3) return 4;
  return 5; // 10
}

type SpinWheelProps = {
  orderId: string;
  sessionId: string;
  onClose: () => void;
  onDone?: () => void;
};

export function SpinWheel({ orderId, sessionId, onClose, onDone }: SpinWheelProps) {
  const [spinning, setSpinning] = useState(false);
  const [result, setResult] = useState<{ points_won: number; message: string } | null>(null);
  const [rotation, setRotation] = useState(0);

  const handleSpin = useCallback(async () => {
    if (spinning) return;
    setSpinning(true);
    setResult(null);
    try {
      const res = await fetch(`/api/orders/${orderId}/spin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      const pointsWon = data.points_won ?? 0;
      const message = data.message ?? (pointsWon === 0 ? "Better luck next time!" : `You won ${pointsWon} AuraPoints!`);
      const index = pointsToSegmentIndex(pointsWon);
      const segmentAngle = 360 / SEGMENTS.length;
      const fullSpins = 5;
      const targetRotation = fullSpins * 360 + (360 - index * segmentAngle);
      setRotation(targetRotation);
      setTimeout(() => {
        setResult({ points_won: pointsWon, message });
        setSpinning(false);
      }, 4500);
    } catch {
      setResult({ points_won: 0, message: "Something went wrong. Try again." });
      setSpinning(false);
    }
  }, [orderId, sessionId, spinning]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="relative w-full max-w-sm rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shadow-2xl overflow-hidden"
      >
        <div className="absolute top-3 right-3 z-10">
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full h-8 w-8" aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-6 pt-10 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Gift className="h-6 w-6 text-amber-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Spin & Win!</h2>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            You placed an order. Spin to win 1–10 AuraPoints for your wallet.
          </p>

          <div className="relative mx-auto mb-6" style={{ width: 260, height: 260 }}>
            {/* Pointer at top */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1 z-10 w-0 h-0 border-l-[14px] border-r-[14px] border-t-[24px] border-l-transparent border-r-transparent border-t-amber-500 drop-shadow-md" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 z-10 w-8 h-4 bg-amber-500 rounded-b-full" />

            {/* Wheel with conic gradient segments */}
            <motion.div
              className="relative w-full h-full rounded-full border-4 border-amber-500/50 shadow-xl"
              style={{ background: conicGradient }}
              animate={{ rotate: rotation }}
              transition={{
                type: "tween",
                ease: [0.2, 0.8, 0.2, 1],
                duration: 4.5,
              }}
            >
              {/* Segment labels - positioned around the wheel */}
              {SEGMENTS.map((label, i) => {
                const angle = (i + 0.5) * SEGMENT_DEG - 90;
                const rad = (angle * Math.PI) / 180;
                const r = 38;
                const x = 50 + r * Math.cos(rad);
                const y = 50 + r * Math.sin(rad);
                return (
                  <span
                    key={i}
                    className="absolute text-xs font-bold text-gray-900 drop-shadow-sm pointer-events-none"
                    style={{
                      left: `${x}%`,
                      top: `${y}%`,
                      transform: `translate(-50%, -50%) rotate(${i * SEGMENT_DEG + SEGMENT_DEG / 2}deg)`,
                    }}
                  >
                    {label}
                  </span>
                );
              })}
              <div className="absolute inset-[18%] rounded-full bg-white dark:bg-gray-900 border-2 border-amber-500/50 flex items-center justify-center shadow-inner">
                <Sparkles className="h-6 w-6 text-amber-500" />
              </div>
            </motion.div>
          </div>

          <AnimatePresence mode="wait">
            {!result ? (
              <motion.div key="spin-btn" initial={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <Button
                  size="lg"
                  onClick={handleSpin}
                  disabled={spinning}
                  className="w-full rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-white font-semibold shadow-lg"
                >
                  {spinning ? "Spinning..." : "Spin the wheel"}
                </Button>
              </motion.div>
            ) : (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                <div
                  className={cn(
                    "rounded-xl py-4 px-4",
                    result.points_won > 0
                      ? "bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800"
                      : "bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                  )}
                >
                  <p className="font-semibold text-gray-900 dark:text-white">
                    {result.points_won > 0 ? (
                      <>🎉 {result.points_won} AuraPoints added to your wallet!</>
                    ) : (
                      <>Better luck next time!</>
                    )}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{result.message}</p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" className="flex-1 rounded-xl" onClick={onClose}>
                    Close
                  </Button>
                  {result.points_won > 0 && (
                    <Button className="flex-1 rounded-xl bg-indigo-600 hover:bg-indigo-700" onClick={onDone}>
                      View wallet
                    </Button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
