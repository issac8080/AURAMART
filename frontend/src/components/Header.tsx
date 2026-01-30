"use client";

import Link from "next/link";
import { ShoppingBag, Sparkles, User, Wallet, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SearchBar } from "@/components/SearchBar";
import { useCart } from "@/app/providers";

export function Header() {
  const { cartCount } = useCart();

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2 font-bold text-xl shrink-0">
            <Sparkles className="h-6 w-6 text-primary" />
            <span className="bg-gradient-to-r from-primary to-purple-600 bg-clip-text text-transparent">
              AuraShop
            </span>
          </Link>
          <SearchBar className="hidden md:block flex-1 max-w-md" />
          <nav className="hidden lg:flex items-center gap-6 text-sm font-medium">
            <Link href="/" className="text-muted-foreground hover:text-primary transition-colors">
              Home
            </Link>
            <Link href="/products" className="text-muted-foreground hover:text-primary transition-colors">
              Products
            </Link>
            <Link href="/discountFrontend" className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
              <Tag className="h-4 w-4" />
              Discounts
            </Link>
            <Link href="/wallet" className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1">
              <Wallet className="h-4 w-4" />
              Wallet
            </Link>
            <Link href="/profile" className="text-muted-foreground hover:text-primary transition-colors">
              Profile
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/wallet">
              <Button variant="ghost" size="icon" title="Aura Wallet">
                <Sparkles className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/profile">
              <Button variant="ghost" size="icon">
                <User className="h-5 w-5" />
              </Button>
            </Link>
            <Link href="/cart">
              <Button variant="ghost" size="icon" className="relative">
                <ShoppingBag className="h-5 w-5" />
                {cartCount != null && cartCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-primary text-[10px] font-bold text-primary-foreground flex items-center justify-center animate-pulse">
                    {cartCount > 9 ? "9+" : cartCount}
                  </span>
                )}
              </Button>
            </Link>
          </div>
        </div>
        <div className="md:hidden pb-3">
          <SearchBar />
        </div>
      </div>
    </header>
  );
}
