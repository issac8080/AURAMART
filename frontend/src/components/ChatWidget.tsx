"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send, Loader2, Sparkles, ShoppingBag, Star, ShoppingCart, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { formatPrice } from "@/lib/utils";
import { getProductImageSrc, getProductImagePlaceholder } from "@/lib/unsplash";
import { useCart } from "@/app/providers";
import { chatStream, fetchProduct, addToCart, type Product } from "@/lib/api";

const SUGGESTED = [
  "Show trending products",
  "Find something under ₹5000",
  "Best casual wear",
  "Gift ideas for tech lover",
  "Check my wallet",
  "What's in my cart?",
];

// Follow-up suggestions shown after assistant messages (generative-AI style)
const FOLLOW_UPS: Record<string, string[]> = {
  default: [
    "Show more like this",
    "What's in my cart?",
    "Best under ₹3000",
    "Tell me about AuraPoints",
  ],
  cart: ["Checkout", "Show recommendations", "Clear cart"],
  products: ["Add to cart", "Show similar", "Filter by price"],
};

// Rich message content: **bold**, lists, links, code
function MessageContent({ content, isStreaming }: { content: string; isStreaming?: boolean }) {
  const lines = content.split("\n");
  return (
    <div className="whitespace-pre-wrap text-sm leading-relaxed space-y-1.5">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        const bullet = /^[-*•]\s+/.exec(trimmed);
        const boldParts = trimmed.split(/(\*\*[^*]+\*\*)/g);
        const rendered = (
          <span key={i}>
            {boldParts.map((part, j) =>
              part.startsWith("**") && part.endsWith("**") ? (
                <strong key={j} className="font-semibold text-foreground">
                  {part.slice(2, -2)}
                </strong>
              ) : (
                <span key={j}>{part}</span>
              )
            )}
          </span>
        );
        if (bullet) {
          return (
            <div key={i} className="flex gap-2">
              <span className="text-primary shrink-0">•</span>
              {rendered}
            </div>
          );
        }
        return <div key={i}>{rendered}</div>;
      })}
      {isStreaming && (
        <span className="inline-block w-2 h-4 ml-0.5 bg-primary/80 animate-pulse align-middle" aria-hidden />
      )}
    </div>
  );
}

export function ChatWidget() {
  const { sessionId, refreshCart } = useCart();
  const [open, setOpen] = useState(false);
  type ChatMessage = { role: "user" | "assistant"; content: string; product_ids?: string[]; isStreaming?: boolean };
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: "Hi! I'm your AuraShop assistant. I can help you search products, check your cart, track orders, and manage your wallet. Pick an option below or type your question.",
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
    setMessages((m) => [...m, { role: "user", content: msg }, { role: "assistant", content: "", product_ids: [], isStreaming: true }]);
    setLoading(true);
    const history = messages.slice(-8).map((m) => ({ role: m.role, content: m.content }));

    await chatStream(sessionId || "", msg, history, {
      onChunk: (chunk) => {
        setMessages((m) => {
          const idx = m.findIndex((x) => x.role === "assistant" && x.isStreaming);
          if (idx < 0) return m;
          const next = [...m];
          next[idx] = { ...next[idx], content: next[idx].content + chunk };
          return next;
        });
      },
      onDone: (productIds) => {
        setMessages((m) => {
          const idx = m.findIndex((x) => x.role === "assistant" && x.isStreaming);
          if (idx < 0) return m;
          const next = [...m];
          next[idx] = { role: "assistant", content: next[idx].content, product_ids: productIds, isStreaming: false };
          return next;
        });
        setLoading(false);
        if (productIds?.length) {
          productIds.forEach((id) => {
            if (!productsInChat[id]) {
              fetchProduct(id).then((p) => setProductsInChat((prev) => ({ ...prev, [id]: p }))).catch(() => {});
            }
          });
        }
      },
      onError: () => {
        setMessages((m) => {
          const idx = m.findIndex((x) => x.role === "assistant" && x.isStreaming);
          if (idx < 0) return m;
          const next = [...m];
          next[idx] = {
            role: "assistant",
            content: "Sorry, I couldn't reach the server. Make sure the backend is running (port 8000).",
            product_ids: [],
            isStreaming: false,
          };
          return next;
        });
        setLoading(false);
      },
    });
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
            className="fixed bottom-20 right-4 sm:right-6 z-50 w-[calc(100vw-2rem)] sm:w-[420px] max-w-[calc(100vw-2rem)] h-[min(85vh,620px)] sm:h-[580px] rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 shadow-xl flex flex-col overflow-hidden"
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
                      <MessageContent content={m.content} isStreaming={m.isStreaming} />
                      {m.role === "assistant" && !m.isStreaming && m.content && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {(FOLLOW_UPS.default.slice(0, 3)).map((s) => (
                            <motion.button
                              key={s}
                              type="button"
                              onClick={() => send(s)}
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              className="text-xs rounded-full border border-indigo-300/50 dark:border-indigo-600/50 bg-indigo-50/50 dark:bg-indigo-950/30 px-2.5 py-1 hover:bg-indigo-100/80 dark:hover:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 font-medium transition-colors"
                            >
                              {s}
                            </motion.button>
                          ))}
                        </div>
                      )}
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
                                  className="flex flex-col rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden w-[160px] flex-shrink-0 hover:border-indigo-400 dark:hover:border-indigo-600 hover:shadow-md transition-all duration-200 group text-left"
                                >
                                  <div className="relative h-28 w-full bg-muted overflow-hidden">
                                    <img
                                      src={getProductImageSrc(p.image_url, p.category, p.id, p.name)}
                                      alt={p.name}
                                      className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                      loading="lazy"
                                      onError={(e) => {
                                        e.currentTarget.src = getProductImagePlaceholder(p.name);
                                      }}
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
                {loading && !messages.some((m) => m.isStreaming) && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl rounded-bl-sm bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center gap-2">
                      <div className="flex gap-1">
                        {[0, 1, 2].map((i) => (
                          <motion.span
                            key={i}
                            className="h-2 w-2 rounded-full bg-indigo-500"
                            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                            transition={{ repeat: Infinity, duration: 0.6, delay: i * 0.12 }}
                          />
                        ))}
                      </div>
                      <span className="text-xs text-gray-500 dark:text-gray-400">Thinking...</span>
                    </div>
                  </div>
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
                      <img
                        src={getProductImageSrc(
                          productsInChat[expandedProductId].image_url,
                          productsInChat[expandedProductId].category,
                          productsInChat[expandedProductId].id,
                          productsInChat[expandedProductId].name
                        )}
                        alt={productsInChat[expandedProductId].name}
                        className="absolute inset-0 w-full h-full object-cover"
                        onError={(e) => {
                          e.currentTarget.src = getProductImagePlaceholder(productsInChat[expandedProductId].name);
                        }}
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

            {/* Added to cart toast */}
            <AnimatePresence>
              {addedToCartMessage && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  className="mx-4 mb-2 py-2.5 px-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-sm font-medium text-center"
                >
                  {addedToCartMessage}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Suggested options (above input) + Ask box */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950/80">
              <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2.5">
                Quick options
              </p>
              <div className="flex flex-wrap gap-2 mb-4">
                {SUGGESTED.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => send(s)}
                    disabled={loading}
                    className="text-xs rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/80 px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 hover:border-indigo-300 dark:hover:border-indigo-700 text-gray-700 dark:text-gray-300 font-medium transition-colors disabled:opacity-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <Input
                  placeholder="Type your question..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send(input)}
                  className="flex-1 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 text-sm"
                />
                <Button
                  size="icon"
                  onClick={() => send(input)}
                  disabled={loading}
                  className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white shrink-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
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
