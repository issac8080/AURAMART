"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trophy, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const SYMBOLS = ["7", "★", "🍒", "🍋"];
const REEL_LENGTH = 12;
const REEL_STRIP = Array.from({ length: REEL_LENGTH }, (_, i) => SYMBOLS[i % SYMBOLS.length]);
const SYMBOL_HEIGHT = 64;
const FULL_SPINS = 4;
const SPIN_DURATION = 2.5;
const STOP_STAGGER = 0.35;

type HomeJackpotProps = {
  won: boolean;
  discount: number;
  code: string | null;
  message: string;
  minOrder: number;
  onClose: () => void;
};

export function HomeJackpot({ won, discount, code, message, minOrder, onClose }: HomeJackpotProps) {
  const [reel1, setReel1] = useState(0);
  const [reel2, setReel2] = useState(0);
  const [reel3, setReel3] = useState(0);
  const [showResult, setShowResult] = useState(false);

  useEffect(() => {
    const winIdx = 0;
    const loseIdxs = [1, 2, 3];
    if (won) {
      setReel1(winIdx);
      setReel2(winIdx);
      setReel3(winIdx);
    } else {
      setReel1(loseIdxs[Math.floor(Math.random() * 3)]);
      setReel2(loseIdxs[Math.floor(Math.random() * 3)]);
      setReel3(loseIdxs[Math.floor(Math.random() * 3)]);
    }
  }, [won]);

  useEffect(() => {
    const totalMs = (SPIN_DURATION + STOP_STAGGER * 2 + 0.5) * 1000;
    const t = setTimeout(() => setShowResult(true), totalMs);
    return () => clearTimeout(t);
  }, []);

  const targetY = (stopIndex: number) => -(FULL_SPINS * REEL_LENGTH + stopIndex) * SYMBOL_HEIGHT;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="relative w-full max-w-sm rounded-2xl border-2 border-amber-400 dark:border-amber-600 bg-gradient-to-b from-amber-50 to-orange-50 dark:from-gray-900 dark:to-gray-950 shadow-2xl overflow-hidden"
      >
        <div className="absolute top-3 right-3 z-10">
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full h-8 w-8" aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-6 pt-10 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Trophy className="h-6 w-6 text-amber-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Jackpot</h2>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">₹2,000 off on orders above ₹50,000</p>

          <div className="flex justify-center gap-1 sm:gap-2 mb-6 bg-gray-900 rounded-xl p-2 border-4 border-amber-500/50 shadow-inner">
            {[reel1, reel2, reel3].map((stopIndex, reelIndex) => (
              <div
                key={reelIndex}
                className="w-14 sm:w-16 overflow-hidden rounded-lg bg-gray-800 flex items-center justify-center relative"
                style={{ height: SYMBOL_HEIGHT + 16 }}
              >
                <motion.div
                  className="flex flex-col items-center justify-start"
                  initial={{ y: 0 }}
                  animate={{ y: targetY(stopIndex) }}
                  transition={{
                    type: "tween",
                    ease: [0.2, 0.8, 0.2, 1],
                    duration: SPIN_DURATION,
                    delay: reelIndex * STOP_STAGGER,
                  }}
                >
                  {[...REEL_STRIP, ...REEL_STRIP, ...REEL_STRIP, ...REEL_STRIP, ...REEL_STRIP].map((sym, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-center text-2xl sm:text-3xl font-bold text-amber-400 shrink-0"
                      style={{ height: SYMBOL_HEIGHT, width: "100%" }}
                    >
                      {sym}
                    </div>
                  ))}
                </motion.div>
              </div>
            ))}
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
                  {won ? "🎉 Jackpot!" : "Better luck next time"}
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
