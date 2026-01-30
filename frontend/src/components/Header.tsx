"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ShoppingBag, Sparkles, User, Wallet, Menu, X, LogIn, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchBar } from "@/components/SearchBar";
import { useCart, useAuth } from "@/app/providers";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/", label: "Home" },
  { href: "/products", label: "Products" },
  { href: "/wallet", label: "Wallet", icon: Wallet },
  { href: "/profile", label: "Profile", icon: User },
];

export function Header() {
  const pathname = usePathname();
  const { cartCount } = useCart();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/20 dark:border-white/5 bg-white/90 dark:bg-gray-950/90 backdrop-blur-2xl shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset] dark:shadow-none">
      {/* Subtle gradient line under nav */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent pointer-events-none" />

      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
        <div className="flex h-16 sm:h-[4.25rem] items-center justify-between gap-4">
          {/* Logo */}
          <Link
            href="/"
            onClick={() => setMobileOpen(false)}
            className="group flex items-center gap-3 shrink-0"
          >
            <motion.span
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.98 }}
              className="flex h-10 w-10 sm:h-11 sm:w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-blue-600 text-white shadow-lg shadow-indigo-500/30 ring-2 ring-white/20 dark:ring-white/10 group-hover:shadow-indigo-500/40 group-hover:ring-indigo-400/30 transition-all duration-300"
            >
              <Sparkles className="h-5 w-5 transition-transform group-hover:rotate-12 duration-300" />
            </motion.span>
            <span className="font-heading font-bold text-xl sm:text-2xl tracking-tight bg-gradient-to-r from-indigo-600 via-purple-600 to-blue-600 bg-clip-text text-transparent group-hover:from-indigo-500 group-hover:via-purple-500 group-hover:to-blue-500 transition-all duration-300">
              AuraShop
            </span>
          </Link>

          {/* Desktop search - glass pill */}
          <div className="hidden md:block flex-1 max-w-md lg:max-w-lg mx-6">
            <div className="rounded-2xl bg-gray-100/80 dark:bg-white/5 border border-gray-200/80 dark:border-white/10 shadow-sm focus-within:border-indigo-400/50 focus-within:ring-2 focus-within:ring-indigo-400/20 focus-within:shadow-md focus-within:shadow-indigo-500/10 transition-all duration-200 [&_input]:border-0 [&_input]:bg-transparent [&_input]:focus-visible:ring-0 [&_input]:rounded-2xl">
              <SearchBar className="w-full" />
            </div>
          </div>

          {/* Desktop nav - pill links */}
          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href || (href !== "/" && pathname.startsWith(href));
              return (
                <Link key={href} href={href}>
                  <motion.span
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={cn(
                      "flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all duration-200",
                      isActive
                        ? "bg-gradient-to-r from-indigo-500/15 to-purple-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-400/20"
                        : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-white/10 border border-transparent"
                    )}
                  >
                    {Icon && <Icon className="h-4 w-4" />}
                    {label}
                  </motion.span>
                </Link>
              );
            })}
            {user ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => logout()}
                className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-gray-600 dark:text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </Button>
            ) : (
              <Link href="/login">
                <motion.span
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold bg-gradient-to-r from-indigo-500/15 to-purple-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-400/20 hover:from-indigo-500/25 hover:to-purple-500/25"
                >
                  <LogIn className="h-4 w-4" />
                  Login
                </motion.span>
              </Link>
            )}
          </nav>

          {/* Right actions */}
          <div className="flex items-center gap-1.5 sm:gap-2">
            <Link href="/wallet" className="lg:hidden">
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 rounded-xl text-gray-600 dark:text-gray-400 hover:text-indigo-600 hover:bg-indigo-500/10 dark:hover:bg-indigo-500/20"
                title="Aura Wallet"
              >
                <Sparkles className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/profile" className="lg:hidden">
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 rounded-xl text-gray-600 dark:text-gray-400 hover:text-indigo-600 hover:bg-indigo-500/10 dark:hover:bg-indigo-500/20"
              >
                <User className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/cart">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative h-10 w-10 rounded-xl text-gray-600 dark:text-gray-400 hover:text-indigo-600 hover:bg-indigo-500/10 dark:hover:bg-indigo-500/20"
                >
                  <ShoppingBag className="h-5 w-5" />
                  {cartCount != null && cartCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 min-w-[1.25rem] h-5 px-1 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 text-[10px] font-bold text-white flex items-center justify-center ring-2 ring-white dark:ring-gray-900 shadow-lg shadow-indigo-500/30">
                      {cartCount > 99 ? "99+" : cartCount}
                    </span>
                  )}
                </Button>
              </motion.div>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden h-10 w-10 rounded-xl text-gray-600 dark:text-gray-400 hover:text-indigo-600 hover:bg-indigo-500/10"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
            >
              <motion.div
                animate={{ rotate: mobileOpen ? 90 : 0 }}
                transition={{ duration: 0.2 }}
              >
                {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </motion.div>
            </Button>
          </div>
        </div>

        {/* Mobile search row */}
        <div className="md:hidden border-t border-gray-200/80 dark:border-white/10 px-4 py-3 bg-gray-50/50 dark:bg-white/[0.02]">
          <SearchBar />
        </div>
      </div>

      {/* Mobile menu - glass panel */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="lg:hidden overflow-hidden border-t border-gray-200/80 dark:border-white/10 bg-white/95 dark:bg-gray-950/95 backdrop-blur-xl"
          >
            <nav className="container mx-auto px-4 py-4 flex flex-col gap-1 max-w-7xl">
              {navLinks.map(({ href, label, icon: Icon }, i) => {
                const isActive = pathname === href || (href !== "/" && pathname.startsWith(href));
                return (
                  <motion.div
                    key={href}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05, duration: 0.2 }}
                  >
                    <Link
                      href={href}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        "flex items-center gap-3 rounded-xl px-4 py-3.5 text-base font-semibold transition-all duration-200",
                        isActive
                          ? "bg-gradient-to-r from-indigo-500/15 to-purple-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-400/20"
                          : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-white/10"
                      )}
                    >
                      {Icon && (
                        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 dark:bg-white/10">
                          <Icon className="h-5 w-5 text-indigo-500" />
                        </span>
                      )}
                      {label}
                    </Link>
                  </motion.div>
                );
              })}
              {user ? (
                <motion.div
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: navLinks.length * 0.05, duration: 0.2 }}
                >
                  <button
                    type="button"
                    onClick={() => { logout(); setMobileOpen(false); }}
                    className="flex items-center gap-3 rounded-xl px-4 py-3.5 text-base font-semibold text-gray-700 dark:text-gray-300 hover:bg-red-50 dark:hover:bg-red-950/30 hover:text-red-600 w-full"
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 dark:bg-white/10">
                      <LogOut className="h-5 w-5 text-indigo-500" />
                    </span>
                    Logout
                  </button>
                </motion.div>
              ) : (
                <motion.div
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: navLinks.length * 0.05, duration: 0.2 }}
                >
                  <Link
                    href="/login"
                    onClick={() => setMobileOpen(false)}
                    className="flex items-center gap-3 rounded-xl px-4 py-3.5 text-base font-semibold bg-gradient-to-r from-indigo-500/15 to-purple-500/15 text-indigo-600 dark:text-indigo-400 border border-indigo-400/20"
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-100 dark:bg-indigo-900/40">
                      <LogIn className="h-5 w-5 text-indigo-500" />
                    </span>
                    Login
                  </Link>
                </motion.div>
              )}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
