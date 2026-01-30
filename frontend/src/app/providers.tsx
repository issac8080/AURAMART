"use client";

import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { getSessionId } from "@/lib/session";
import { getCart } from "@/lib/api";

const AURA_USER_KEY = "aura_user";

export type AuthUser = { email: string; name: string };

type CartContextType = {
  cartCount: number;
  refreshCart: () => Promise<void>;
  sessionId: string;
};

type AuthContextType = {
  user: AuthUser | null;
  login: (email: string, name: string) => void;
  logout: () => void;
};

const CartContext = createContext<CartContextType | null>(null);
const AuthContext = createContext<AuthContextType | null>(null);

function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(AURA_USER_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as AuthUser;
    return data?.email && data?.name ? data : null;
  } catch {
    return null;
  }
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState("");
  const [cartCount, setCartCount] = useState(0);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  const login = useCallback((email: string, name: string) => {
    const u = { email, name };
    setUser(u);
    try {
      localStorage.setItem(AURA_USER_KEY, JSON.stringify(u));
    } catch {}
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    try {
      localStorage.removeItem(AURA_USER_KEY);
    } catch {}
  }, []);

  const refreshCart = useCallback(async () => {
    const sid = getSessionId();
    setSessionId(sid);
    try {
      const { cart } = await getCart(sid);
      setCartCount(cart.length);
    } catch {
      setCartCount(0);
    }
  }, []);

  useEffect(() => {
    const sid = getSessionId();
    setSessionId(sid);
    getCart(sid)
      .then(({ cart }) => setCartCount(cart.length))
      .catch(() => setCartCount(0));
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <CartContext.Provider value={{ cartCount, refreshCart, sessionId }}>
        {children}
      </CartContext.Provider>
    </AuthContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within Providers");
  return ctx;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within Providers");
  return ctx;
}
