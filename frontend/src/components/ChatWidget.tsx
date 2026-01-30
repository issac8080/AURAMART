"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send, Loader2, Sparkles, ShoppingBag, Star, ShoppingCart, ChevronDown } from "lucide-react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { formatPrice } from "@/lib/utils";
import { getProductImage } from "@/lib/unsplash";
import { useCart } from "@/app/providers";
import { chat, fetchProduct, addToCart, type Product } from "@/lib/api";

const SUGGESTED = [
  "Show trending products",
  "Find something under ₹5000",
  "Best casual wear",
  "Gift ideas for tech lover",
  "Check my wallet",
  "What's in my cart?",
];

// Render message with **bold** support
function MessageContent({ content }: { content: string }) {
  const parts = content.split(/(\*\*[^*]+\*\*)/g);
  return (
    <p className="whitespace-pre-wrap text-fluid-sm leading-relaxed">
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={i} className="font-semibold text-foreground">
            {part.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </p>
  );
}

export function ChatWidget() {
  const { sessionId, refreshCart } = useCart();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string; product_ids?: string[] }[]>([
    {
      role: "assistant",
      content: "Hi! ✨ I'm your AuraShop AI assistant. I can help you **search products**, **check your cart**, **track orders**, and **manage your wallet**. What would you like to do?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [productsInChat, setProductsInChat] = useState<Record<string, Product>>({});
  const [expandedProductId, setExpandedProductId] = useState<string | null>(null);
  const [addingToCartId, setAddingToCartId] = useState<string | null>(null);
  const [addedToCartMessage, setAddedToCartMessage] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, productsInChat, expandedProductId]);

  const handleAddToCartInChat = async (product: Product) => {
    if (!sessionId || addingToCartId) return;
    setAddingToCartId(product.id);
    try {
      await addToCart(sessionId, product.id);
      await refreshCart();
      setAddedToCartMessage(`Added "${product.name}" to cart!`);
      setExpandedProductId(null);
      setTimeout(() => setAddedToCartMessage(null), 2500);
    } catch {
      setAddedToCartMessage("Could not add to cart. Try again.");
      setTimeout(() => setAddedToCartMessage(null), 2000);
    } finally {
      setAddingToCartId(null);
    }
  };

  const send = async (text: string) => {
    const msg = text.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: msg }]);
    setLoading(true);
    try {
      const history = messages.slice(-8).map((m) => ({ role: m.role, content: m.content }));
      const res = await chat(sessionId || "", msg, history);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.content, product_ids: res.product_ids },
      ]);
      if (res.product_ids?.length) {
        const seen = { ...productsInChat };
        for (const id of res.product_ids) {
          if (!seen[id]) {
            try {
              const p = await fetchProduct(id);
              seen[id] = p;
            } catch {
              // ignore
            }
          }
        }
        setProductsInChat(seen);
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Sorry, I couldn't process that. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ type: "spring", damping: 28, stiffness: 320 }}
            className="fixed bottom-20 right-4 sm:right-6 z-50 w-[calc(100vw-2rem)] sm:w-[420px] max-w-[calc(100vw-2rem)] h-[min(85vh,620px)] sm:h-[580px] rounded-2xl sm:rounded-3xl glass-card flex flex-col overflow-hidden glow-ai"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/20 bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-blue-500/10">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={{ rotate: [0, 5, -5, 0] }}
                  transition={{ repeat: Infinity, duration: 3 }}
                  className="h-11 w-11 rounded-xl bg-gradient-to-br from-primary to-purple-600 flex items-center justify-center shadow-lg ring-2 ring-white/30"
                >
                  <Sparkles className="h-5 w-5 text-white" />
                </motion.div>
                <div>
                  <p className="font-bold text-sm text-foreground">AI Shopping Assistant</p>
                  <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse ring-2 ring-emerald-500/30" />
                    Online & ready to help
                  </p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setOpen(false)} aria-label="Close chat" className="rounded-full hover:bg-primary/10">
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Messages */}
            <div
              className="flex-1 overflow-y-auto p-4 space-y-1 bg-gradient-to-b from-muted/30 to-background"
              ref={scrollRef}
            >
              <div className="space-y-4">
                {messages.map((m, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i === messages.length - 1 ? 0.1 : 0 }}
                    className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
                  >
                    <div
                      className={cn(
                        "max-w-[88%] rounded-2xl px-4 py-3 shadow-sm",
                        m.role === "user"
                          ? "bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-br-md"
                          : "glass-card rounded-bl-md text-foreground border-indigo-500/20 shadow-glow"
                      )}
                    >
                      <MessageContent content={m.content} />
                      {m.role === "assistant" && m.product_ids?.length ? (
                        <div className="mt-4 flex gap-3 overflow-x-auto pb-1 -mx-1 scrollbar-thin">
                          {m.product_ids.slice(0, 4).map((id, idx) => {
                            const p = productsInChat[id];
                            if (!p)
                              return (
                                <div
                                  key={id}
                                  className="flex-shrink-0 w-[160px] h-[200px] rounded-xl bg-muted animate-pulse"
                                />
                              );
                            return (
                              <motion.div
                                key={id}
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: idx * 0.05 }}
                              >
                                <button
                                  type="button"
                                  onClick={() => setExpandedProductId(expandedProductId === id ? null : id)}
                                  className="flex flex-col rounded-xl border-2 border-border/80 bg-background overflow-hidden w-[160px] flex-shrink-0 hover:border-primary hover:shadow-lg hover:shadow-primary/10 transition-all duration-200 group text-left"
                                >
                                  <div className="relative h-28 w-full bg-muted overflow-hidden">
                                    <Image
                                      src={getProductImage(p.category, p.id)}
                                      alt={p.name}
                                      fill
                                      className="object-cover group-hover:scale-105 transition-transform duration-300"
                                      sizes="160px"
                                    />
                                    <div className="absolute top-1.5 right-1.5 flex items-center gap-0.5 rounded-full bg-black/50 px-1.5 py-0.5 text-xs text-white">
                                      <Star className="h-3 w-3 fill-current" />
                                      {p.rating}
                                    </div>
                                  </div>
                                  <div className="p-2.5">
                                    <p className="font-medium text-xs line-clamp-2 text-foreground">{p.name}</p>
                                    <p className="text-primary font-bold text-sm mt-0.5">{formatPrice(p.price)}</p>
                                    {p.category && (
                                      <p className="text-[10px] text-muted-foreground truncate">{p.category}</p>
                                    )}
                                    <p className="text-[10px] text-primary/80 mt-1 flex items-center gap-0.5">
                                      <ChevronDown className="h-3 w-3" /> Tap for details
                                    </p>
                                  </div>
                                </button>
                              </motion.div>
                            );
                          })}
                        </div>
                      ) : null}
                    </div>
                  </motion.div>
                ))}
                {loading && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                  >
                    <div className="rounded-2xl rounded-bl-md bg-card border border-border/80 px-4 py-3 flex items-center gap-2">
                      <div className="flex gap-1">
                        {[0, 1, 2].map((i) => (
                          <motion.span
                            key={i}
                            className="h-2 w-2 rounded-full bg-primary/60"
                            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                            transition={{ repeat: Infinity, duration: 0.8, delay: i * 0.15 }}
                          />
                        ))}
                      </div>
                      <span className="text-xs text-muted-foreground">Thinking...</span>
                    </div>
                  </motion.div>
                )}
              </div>
            </div>

            {/* Inline product detail (no redirect – all in chat) */}
            <AnimatePresence>
              {expandedProductId && productsInChat[expandedProductId] && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ type: "spring", damping: 25 }}
                  className="border-t border-border/80 bg-card overflow-hidden"
                >
                  <div className="p-4 flex gap-4">
                    <div className="relative w-24 h-24 rounded-xl bg-muted flex-shrink-0 overflow-hidden">
                      <Image
                        src={getProductImage(productsInChat[expandedProductId].category, productsInChat[expandedProductId].id)}
                        alt={productsInChat[expandedProductId].name}
                        fill
                        unoptimized
                        className="object-cover"
                        sizes="96px"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm line-clamp-2">{productsInChat[expandedProductId].name}</p>
                      <p className="text-primary font-bold mt-0.5">{formatPrice(productsInChat[expandedProductId].price)}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                        <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                        {productsInChat[expandedProductId].rating} · {productsInChat[expandedProductId].category}
                      </p>
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-2">{productsInChat[expandedProductId].description}</p>
                      <div className="flex gap-2 mt-3">
                        <Button
                          size="sm"
                          onClick={() => handleAddToCartInChat(productsInChat[expandedProductId])}
                          disabled={!!addingToCartId}
                          className="rounded-lg gap-1.5"
                        >
                          {addingToCartId === expandedProductId ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <ShoppingCart className="h-3.5 w-3.5" />
                          )}
                          {addingToCartId === expandedProductId ? "Adding..." : "Add to cart"}
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => setExpandedProductId(null)} className="rounded-lg">
                          Close
                        </Button>
                      </div>
                    </div>
                    <Button variant="ghost" size="icon" onClick={() => setExpandedProductId(null)} className="flex-shrink-0 rounded-full" aria-label="Close">
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Added to cart toast (in-chat only) */}
            <AnimatePresence>
              {addedToCartMessage && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 8 }}
                  className="px-3 py-2 mx-3 mt-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-sm font-medium text-center"
                >
                  {addedToCartMessage}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Input + Suggested */}
            <div className="p-3 border-t bg-card/80 backdrop-blur-sm">
              <div className="flex gap-2">
                <Input
                  placeholder="Ask anything—search, cart, wallet..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send(input)}
                  className="flex-1 rounded-xl border-2 focus:border-primary/50 bg-background"
                />
                <Button
                  size="icon"
                  onClick={() => send(input)}
                  disabled={loading}
                  className="rounded-xl bg-gradient-to-br from-primary to-purple-600 hover:opacity-90 shadow-lg"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                {SUGGESTED.map((s, i) => (
                  <motion.button
                    key={s}
                    type="button"
                    onClick={() => send(s)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="text-xs rounded-full border-2 border-primary/20 bg-gradient-to-r from-primary/5 to-purple-500/5 px-3 py-1.5 hover:border-primary/40 hover:from-primary/10 hover:to-purple-500/10 transition-colors font-medium text-foreground/90"
                  >
                    {s}
                  </motion.button>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB - glowing AI assistant */}
      <motion.button
        whileHover={{ scale: 1.08, boxShadow: "0 0 32px -4px rgba(99, 102, 241, 0.5), 0 0 48px -8px rgba(34, 211, 238, 0.3)" }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-4 right-4 sm:right-5 z-50 h-12 w-12 sm:h-14 sm:w-14 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-blue-600 text-white shadow-glow-lg flex items-center justify-center border border-white/20 transition-all duration-200"
        aria-label="Open AI assistant"
      >
        <MessageCircle className="h-5 w-5 sm:h-6 sm:w-6" />
        <span className="absolute -top-0.5 -right-0.5 h-3 w-3 sm:h-3.5 sm:w-3.5 rounded-full bg-cyan-400 border-2 border-background animate-pulse shadow-lg shadow-cyan-400/50" />
      </motion.button>
    </>
  );
}
