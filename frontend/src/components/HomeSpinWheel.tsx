"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Ticket, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const SEGMENTS = ["₹1000", "Better luck", "₹1000", "Better luck", "₹1000", "Better luck"];
const SEGMENT_DEG = 360 / SEGMENTS.length;
const WIN_INDICES = [0, 2, 4];
const LOSE_INDICES = [1, 3, 5];
const SEGMENT_HEX = ["#fde68a", "#e5e7eb", "#fde68a", "#e5e7eb", "#fde68a", "#e5e7eb"];
const conicGradient = `conic-gradient(${SEGMENT_HEX.map((c, i) => `${c} ${i * SEGMENT_DEG}deg ${(i + 1) * SEGMENT_DEG}deg`).join(", ")})`;

type HomeSpinWheelProps = {
  won: boolean;
  discount: number;
  code: string | null;
  message: string;
  minOrder: number;
  onClose: () => void;
};

export function HomeSpinWheel({ won, discount, code, message, minOrder, onClose }: HomeSpinWheelProps) {
  const [rotation, setRotation] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [startSpin, setStartSpin] = useState(false);

  const targetIndex = useMemo(() => {
    if (won) return WIN_INDICES[Math.floor(Math.random() * WIN_INDICES.length)];
    return LOSE_INDICES[Math.floor(Math.random() * LOSE_INDICES.length)];
  }, [won]);

  useEffect(() => {
    const fullSpins = 6;
    const targetRotation = fullSpins * 360 + (360 - targetIndex * SEGMENT_DEG);
    const spinDelay = setTimeout(() => {
      setStartSpin(true);
      setRotation(targetRotation);
    }, 400);
    const resultDelay = setTimeout(() => setShowResult(true), 5500);
    return () => {
      clearTimeout(spinDelay);
      clearTimeout(resultDelay);
    };
  }, [targetIndex]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="relative w-full max-w-sm rounded-2xl border border-amber-200 dark:border-amber-800 bg-white dark:bg-gray-950 shadow-2xl overflow-hidden"
      >
        <div className="absolute top-3 right-3 z-10">
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full h-8 w-8" aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-6 pt-10 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Ticket className="h-6 w-6 text-amber-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Spin the Wheel</h2>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">₹1,000 off on orders above ₹50,000</p>

          <div className="relative mx-auto mb-6" style={{ width: 260, height: 260 }}>
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1 z-10 w-0 h-0 border-l-[14px] border-r-[14px] border-t-[24px] border-l-transparent border-r-transparent border-t-amber-500 drop-shadow-md" />
            <div className="absolute top-0 left-1/2 -translate-x-1/2 z-10 w-8 h-4 bg-amber-500 rounded-b-full" />

            <motion.div
              className="relative w-full h-full rounded-full border-4 border-amber-500/50 shadow-xl"
              style={{ background: conicGradient }}
              initial={false}
              animate={{ rotate: startSpin ? rotation : 0 }}
              transition={{
                type: "tween",
                ease: [0.12, 0.6, 0.15, 1],
                duration: 5,
              }}
            >
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
                <span className="text-xs font-semibold text-amber-600">SPIN</span>
              </div>
            </motion.div>
          </div>

          <AnimatePresence>
            {showResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`rounded-xl p-4 border-2 ${
                  won
                    ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800"
                    : "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
                }`}
              >
                <p className="font-semibold text-gray-900 dark:text-white">
                  {won ? "🎉 You won!" : "Better luck next time"}
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{message}</p>
                {won && code && (
                  <p className="mt-2 text-sm font-mono font-bold text-emerald-700 dark:text-emerald-400">
                    Code: {code} (min order ₹{minOrder.toLocaleString()})
                  </p>
                )}
                <Button className="mt-4 w-full" onClick={onClose}>
                  Close
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
