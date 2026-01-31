"use client";

import { createContext, useContext, useState, useCallback, useEffect, useMemo } from "react";
import { getSessionId } from "@/lib/session";
import { getCart } from "@/lib/api";

const AURA_USER_KEY = "aura_user";
const LOGIN_COOKIE = "aura_logged_in";

function setLoginCookie(loggedIn: boolean) {
  if (typeof document === "undefined") return;
  if (loggedIn) {
    document.cookie = `${LOGIN_COOKIE}=1; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax`;
  } else {
    document.cookie = `${LOGIN_COOKIE}=; path=/; max-age=0`;
  }
}

export type AuthUser = { email: string; name: string; user_id: string };

type CartContextType = {
  cartCount: number;
  refreshCart: () => Promise<void>;
  sessionId: string;
};

type AuthContextType = {
  user: AuthUser | null;
  login: (email: string, name: string, user_id: string) => void;
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
    return data?.email && data?.name && data?.user_id ? data : null;
  } catch {
    return null;
  }
}

function getInitialSessionId(): string {
  if (typeof window === "undefined") return "";
  return getSessionId();
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState(getInitialSessionId);
  const [cartCount, setCartCount] = useState(0);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const u = getStoredUser();
    setUser(u);
    setLoginCookie(!!u);
  }, []);

  const login = useCallback((email: string, name: string, user_id: string) => {
    const u = { email, name, user_id };
    setUser(u);
    setLoginCookie(true);
    try {
      localStorage.setItem(AURA_USER_KEY, JSON.stringify(u));
    } catch {}
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setLoginCookie(false);
    try {
      localStorage.removeItem(AURA_USER_KEY);
    } catch {}
  }, []);

  useEffect(() => {
    const syncUser = () => {
      const u = getStoredUser();
      setUser(u);
      setLoginCookie(!!u);
    };
    window.addEventListener("storage", syncUser);
    return () => window.removeEventListener("storage", syncUser);
  }, []);

  const authValue = useMemo(() => ({ user, login, logout }), [user, login, logout]);

  const refreshCart = useCallback(async () => {
    const sid = getSessionId();
    setSessionId(sid);
    const uid = getStoredUser()?.user_id;
    try {
      const { cart } = await getCart(sid);
      const count = Array.isArray(cart)
        ? cart.reduce((s, p) => s + (typeof (p as any).quantity === "number" ? (p as any).quantity : 1), 0)
        : 0;
      setCartCount(count);
    } catch {
      setCartCount(0);
    }
  }, []);

  useEffect(() => {
    const sid = getSessionId();
    setSessionId(sid);
    if (!sid) return;
    getCart(sid)
      .then(({ cart }) => {
        const count = Array.isArray(cart)
          ? cart.reduce((s, p) => s + (typeof (p as any).quantity === "number" ? (p as any).quantity : 1), 0)
          : 0;
        setCartCount(count);
      })
      .catch(() => setCartCount(0));
  }, []);

  return (
    <AuthContext.Provider value={authValue}>
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
