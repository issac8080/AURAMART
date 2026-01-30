"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ShoppingBag, Sparkles, User, Wallet, Tag, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchBar } from "@/components/SearchBar";
import { useCart } from "@/app/providers";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/products", label: "Products" },
  { href: "/discountFrontend", label: "Discounts", icon: Tag },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/profile", label: "Profile", icon: User },
];

export function Header() {
  const { cartCount } = useCart();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-white/20 bg-white/80 dark:bg-background/90 backdrop-blur-2xl supports-[backdrop-filter]:bg-white/70 dark:supports-[backdrop-filter]:bg-background/70 shadow-sm">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
        <div className="flex h-14 sm:h-16 items-center justify-between gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 shrink-0 font-heading font-bold text-xl tracking-tight"
            onClick={() => setMobileOpen(false)}
          >
            <span className="flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-blue-600 text-white shadow-lg shadow-primary/30">
              <Sparkles className="h-4 w-4 sm:h-5 sm:w-5" />
            </span>
            <span className="text-gradient-ai font-bold">
              AuraShop
            </span>
          </Link>

          <SearchBar className="hidden md:block flex-1 max-w-sm lg:max-w-md mx-4" />

          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-2 text-fluid-sm font-medium text-muted-foreground",
                  "hover:text-foreground hover:bg-accent/80 transition-colors"
                )}
              >
                {Icon && <Icon className="h-4 w-4" />}
                {label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-1 sm:gap-2">
            <Link href="/wallet" className="lg:hidden">
              <Button variant="ghost" size="icon" className="h-10 w-10 rounded-xl" title="Aura Wallet">
                <Sparkles className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/profile" className="lg:hidden">
              <Button variant="ghost" size="icon" className="h-10 w-10 rounded-xl">
                <User className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/cart">
              <Button variant="ghost" size="icon" className="relative h-10 w-10 rounded-xl">
                <ShoppingBag className="h-5 w-5" />
                {cartCount != null && cartCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 h-5 w-5 rounded-full bg-primary text-[10px] font-bold text-primary-foreground flex items-center justify-center ring-2 ring-background">
                    {cartCount > 9 ? "9+" : cartCount}
                  </span>
                )}
              </Button>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-10 w-10 rounded-xl"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>

        <div className="md:hidden border-t border-border/60 px-4 py-3">
          <SearchBar />
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="lg:hidden overflow-hidden border-b border-border/80 bg-card/95 backdrop-blur-xl"
          >
            <nav className="container mx-auto px-4 py-4 flex flex-col gap-1 max-w-7xl">
              {navLinks.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className="flex items-center gap-3 rounded-xl px-4 py-3 text-fluid-base font-medium text-foreground hover:bg-accent transition-colors"
                >
                  {Icon && <Icon className="h-5 w-5 text-muted-foreground" />}
                  {label}
                </Link>
              ))}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
