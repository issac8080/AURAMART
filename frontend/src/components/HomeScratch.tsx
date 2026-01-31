"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Scissors, X } from "lucide-react";
import { Button } from "@/components/ui/button";

type HomeScratchProps = {
  won: boolean;
  discount: number;
  code: string | null;
  message: string;
  minOrder: number;
  onClose: () => void;
};

const CARD_WIDTH = 280;
const CARD_HEIGHT = 160;
const BRUSH_SIZE = 24;

export function HomeScratch({ won, discount, code, message, minOrder, onClose }: HomeScratchProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [scratchPercent, setScratchPercent] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const isScratching = useRef(false);
  const lastPoint = useRef<{ x: number; y: number } | null>(null);

  const initCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = CARD_WIDTH;
    canvas.height = CARD_HEIGHT;
    ctx.fillStyle = "#9ca3af";
    ctx.fillRect(0, 0, CARD_WIDTH, CARD_HEIGHT);
    ctx.globalCompositeOperation = "destination-out";
  }, []);

  useEffect(() => {
    initCanvas();
  }, [initCanvas]);

  const scratch = useCallback(
    (clientX: number, clientY: number) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      const x = (clientX - rect.left) * scaleX;
      const y = (clientY - rect.top) * scaleY;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.beginPath();
      ctx.arc(x, y, BRUSH_SIZE, 0, Math.PI * 2);
      ctx.fill();
      if (lastPoint.current) {
        const dx = x - lastPoint.current.x;
        const dy = y - lastPoint.current.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const steps = Math.max(1, Math.floor(dist / (BRUSH_SIZE / 2)));
        for (let i = 1; i <= steps; i++) {
          const tx = lastPoint.current.x + (dx * i) / steps;
          const ty = lastPoint.current.y + (dy * i) / steps;
          ctx.beginPath();
          ctx.arc(tx, ty, BRUSH_SIZE, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      lastPoint.current = { x, y };
      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const data = imageData.data;
      let transparent = 0;
      for (let i = 3; i < data.length; i += 4) {
        if (data[i] < 128) transparent++;
      }
      const pct = (transparent / (canvas.width * canvas.height)) * 100;
      setScratchPercent(pct);
      if (pct > 55 && !revealed) setRevealed(true);
    },
    [revealed]
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      isScratching.current = true;
      lastPoint.current = null;
      scratch(e.clientX, e.clientY);
    },
    [scratch]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isScratching.current) return;
      scratch(e.clientX, e.clientY);
    },
    [scratch]
  );

  const handlePointerUp = useCallback(() => {
    isScratching.current = false;
    lastPoint.current = null;
  }, []);

  useEffect(() => {
    const onUp = () => isScratching.current = false;
    window.addEventListener("pointerup", onUp);
    return () => window.removeEventListener("pointerup", onUp);
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="relative w-full max-w-sm rounded-2xl border-2 border-amber-200 dark:border-amber-800 bg-white dark:bg-gray-950 shadow-2xl overflow-hidden"
      >
        <div className="absolute top-3 right-3 z-10">
          <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full h-8 w-8" aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-6 pt-10 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Scissors className="h-6 w-6 text-amber-500" />
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Lucky Scratch</h2>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">₹500 off on orders above ₹50,000</p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Scratch the card to reveal your prize</p>

          <div
            className="relative mx-auto rounded-xl overflow-hidden border-2 border-amber-400 shadow-lg touch-none"
            style={{ width: CARD_WIDTH, height: CARD_HEIGHT }}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={handlePointerUp}
          >
            <div
              className="absolute inset-0 flex flex-col items-center justify-center p-4 rounded-xl"
              style={{
                background: won
                  ? "linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)"
                  : "linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)",
              }}
            >
              <p className="font-bold text-lg text-gray-900 dark:text-gray-900">
                {won ? "🎉 You won!" : "Better luck next time"}
              </p>
              <p className="text-sm text-gray-700 dark:text-gray-700 mt-1">{message}</p>
              {won && code && (
                <p className="mt-2 text-sm font-mono font-bold text-emerald-800">
                  Code: {code} (min order ₹{minOrder.toLocaleString()})
                </p>
              )}
            </div>
            <canvas
              ref={canvasRef}
              className="absolute inset-0 w-full h-full cursor-crosshair"
              style={{ width: CARD_WIDTH, height: CARD_HEIGHT }}
            />
          </div>

          <AnimatePresence>
            {revealed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="mt-4"
              >
                <Button className="w-full" onClick={onClose}>
                  Close
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
          {!revealed && scratchPercent > 0 && (
            <p className="text-xs text-gray-500 mt-2">Scratch to reveal ({Math.round(scratchPercent)}%)</p>
          )}
        </div>
      </motion.div>
    </div>
  );
}
