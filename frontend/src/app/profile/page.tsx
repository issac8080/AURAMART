"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  User,
  Package,
  MapPin,
  Store,
  Edit,
  Mail,
  Phone,
  ChevronRight,
  Wallet,
  ShoppingBag,
  CheckCircle2,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useCart, useAuth } from "@/app/providers";
import { formatPrice } from "@/lib/utils";

const API = "/api";

type Order = {
  id: string;
  total: number;
  status: string;
  delivery_method: string;
  created_at: string;
};

type Profile = {
  user_id: string;
  name?: string;
  email?: string;
  phone?: string;
  addresses: string[];
  preferred_stores: string[];
};

export default function ProfilePage() {
  const { sessionId } = useCart();
  const { user: authUser } = useAuth();
  const userId = sessionId;
  const [profile, setProfile] = useState<Profile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authUser) {
      setName((n) => n || authUser.name);
      setEmail((e) => e || authUser.email);
    }
  }, [authUser]);

  useEffect(() => {
    async function loadProfile() {
      try {
        const res = await fetch(`${API}/users/${userId}/profile`);
        if (res.ok) {
          const data = await res.json();
          setProfile(data);
          setName(data.name || authUser?.name || "");
          setEmail(data.email || authUser?.email || "");
          setPhone(data.phone || "");
        } else if (authUser) {
          setName(authUser.name);
          setEmail(authUser.email);
        }
      } catch {
        if (authUser) {
          setName(authUser.name);
          setEmail(authUser.email);
        }
      }
    }
    async function loadOrders() {
      try {
        const res = await fetch(`${API}/users/${userId}/orders`);
        const data = await res.json();
        setOrders(data.orders || []);
      } catch {}
    }
    if (userId) {
      Promise.all([loadProfile(), loadOrders()]).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [userId, authUser]);

  const handleSaveProfile = async () => {
    try {
      const res = await fetch(`${API}/users/${userId}/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, phone }),
      });
      const data = await res.json();
      setProfile(data);
      setEditing(false);
    } catch {
      alert("Failed to update profile");
    }
  };

  const statusConfig: Record<string, { label: string; className: string }> = {
    pending: { label: "Pending", className: "bg-amber-100 text-amber-800 dark:bg-amber-500/20 dark:text-amber-300 border-amber-200 dark:border-amber-500/30" },
    confirmed: { label: "Confirmed", className: "bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-300 border-blue-200 dark:border-blue-500/30" },
    ready_for_pickup: { label: "Ready for pickup", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30" },
    delivered: { label: "Delivered", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30" },
    picked_up: { label: "Picked up", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-300 border-emerald-200 dark:border-emerald-500/30" },
  };

  const completedCount = orders.filter((o) => o.status === "delivered" || o.status === "picked_up").length;

  if (loading) {
    return (
      <div className="py-6 sm:py-8 lg:py-10 space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-2">
            <div className="h-9 w-56 rounded-xl bg-gradient-to-r from-gray-200 to-gray-100 dark:from-gray-800 dark:to-gray-700/80 animate-pulse" />
            <div className="h-4 w-40 rounded-lg bg-gray-100 dark:bg-gray-800/60 animate-pulse" />
          </div>
          <div className="flex gap-2">
            <div className="h-10 w-28 rounded-xl bg-gray-100 dark:bg-gray-800/60 animate-pulse" />
            <div className="h-10 w-32 rounded-xl bg-gray-100 dark:bg-gray-800/60 animate-pulse" />
          </div>
        </div>
        <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
          <div className="space-y-6">
            <div className="h-72 rounded-2xl border border-gray-200 dark:border-gray-700 bg-gradient-to-b from-white to-gray-50 dark:from-gray-900/50 dark:to-gray-800/30 animate-pulse" />
            <div className="h-44 rounded-2xl border border-gray-200 dark:border-gray-700 bg-gradient-to-b from-white to-indigo-50/20 dark:from-gray-900/50 dark:to-indigo-950/10 animate-pulse" />
          </div>
          <div className="md:col-span-2 h-[28rem] rounded-2xl border border-gray-200 dark:border-gray-700 bg-gradient-to-b from-white to-gray-50 dark:from-gray-900/50 dark:to-gray-800/30 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="py-6 sm:py-8 lg:py-10 space-y-8 sm:space-y-10">
      {/* Page header – premium with gradient accent */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-gray-900 dark:text-white">
            My Profile
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Manage your account, orders, and preferences
          </p>
        </div>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          <Link href="/wallet">
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl font-semibold border-2 border-indigo-200 dark:border-indigo-800 hover:border-indigo-400 dark:hover:border-indigo-600 hover:bg-indigo-50/80 dark:hover:bg-indigo-500/10 hover:shadow-md hover:shadow-indigo-500/10 transition-all duration-200"
            >
              <Wallet className="h-4 w-4 mr-2 text-indigo-500" />
              Aura Wallet
            </Button>
          </Link>
          <Link href="/products">
            <Button
              size="sm"
              className="rounded-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 hover:shadow-xl hover:shadow-indigo-500/30 text-white border-0 shadow-lg shadow-indigo-500/25 transition-all duration-200"
            >
              <ShoppingBag className="h-4 w-4 mr-2" />
              Start Shopping
            </Button>
          </Link>
        </div>
      </motion.div>

      <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
        {/* Left column – Profile + Quick Stats */}
        <div className="space-y-6">
          {/* Profile card */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="rounded-2xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50 shadow-lg overflow-hidden">
              <div className="h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500" />
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="font-heading text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
                      <User className="h-5 w-5" />
                    </div>
                    Profile
                  </CardTitle>
                    {!editing && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditing(true)}
                      className="rounded-xl text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 border border-transparent hover:border-indigo-200 dark:hover:border-indigo-800 transition-all duration-200"
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {editing ? (
                  <>
                    <div>
                      <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Name</label>
                      <Input
                        placeholder="Your name"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="mt-1.5 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Email</label>
                      <Input
                        type="email"
                        placeholder="your@email.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="mt-1.5 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Phone</label>
                      <Input
                        type="tel"
                        placeholder="Phone number"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        className="mt-1.5 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                      />
                    </div>
                    <div className="flex gap-2 pt-2">
                      <Button
                        onClick={handleSaveProfile}
                        className="flex-1 rounded-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 shadow-lg shadow-indigo-500/25 text-white border-0 transition-all duration-200"
                      >
                        Save
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setEditing(false)}
                        className="flex-1 rounded-xl font-semibold border-2 border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                      >
                        Cancel
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="space-y-3">
                    {profile?.name && (
                      <div className="flex items-center gap-3 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/40 px-4 py-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 dark:bg-indigo-500/20">
                          <User className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
                        </div>
                        <span className="font-medium text-gray-900 dark:text-white">{profile.name}</span>
                      </div>
                    )}
                    {profile?.email && (
                      <div className="flex items-center gap-3 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/40 px-4 py-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 dark:bg-indigo-500/20">
                          <Mail className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
                        </div>
                        <span className="font-medium text-gray-900 dark:text-white">{profile.email}</span>
                      </div>
                    )}
                    {profile?.phone && (
                      <div className="flex items-center gap-3 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/40 px-4 py-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 dark:bg-indigo-500/20">
                          <Phone className="h-4 w-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
                        </div>
                        <span className="font-medium text-gray-900 dark:text-white">{profile.phone}</span>
                      </div>
                    )}
                    {!profile?.name && !profile?.email && !profile?.phone && (
                      <div className="rounded-2xl border-2 border-dashed border-indigo-200 dark:border-indigo-800/50 bg-indigo-50/30 dark:bg-indigo-950/20 p-8 text-center">
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          No profile information yet. Click Edit to add details.
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setEditing(true)}
                          className="mt-4 rounded-xl border-indigo-300 dark:border-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-500/10"
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Add details
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Quick Stats – premium gradient card */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.3 }}
          >
            <Card className="rounded-2xl border-2 border-indigo-100 dark:border-indigo-900/40 bg-gradient-to-br from-indigo-50/60 to-purple-50/40 dark:from-indigo-950/30 dark:to-purple-950/20 shadow-xl shadow-indigo-500/5 overflow-hidden">
              <div className="h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500" />
              <CardHeader className="pb-2">
                <CardTitle className="font-heading text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/20">
                    <Package className="h-4 w-4" />
                  </div>
                  Quick Stats
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between rounded-xl bg-white/80 dark:bg-gray-800/60 backdrop-blur px-4 py-3.5 border border-indigo-100 dark:border-indigo-900/40 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Orders</span>
                  <span className="font-heading text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                    {orders.length}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-white/80 dark:bg-gray-800/60 backdrop-blur px-4 py-3.5 border border-indigo-100 dark:border-indigo-900/40 shadow-sm hover:shadow-md transition-shadow">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Completed</span>
                  <span className="font-heading text-2xl font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                    <CheckCircle2 className="h-6 w-6" />
                    {completedCount}
                  </span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Right column – Orders */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3 }}
          className="md:col-span-2"
        >
          <Card className="rounded-2xl border-2 border-indigo-100 dark:border-indigo-900/40 bg-gradient-to-b from-white to-indigo-50/20 dark:from-gray-900/80 dark:to-indigo-950/20 shadow-xl shadow-indigo-500/5 overflow-hidden h-full hover:shadow-indigo-500/10 transition-shadow duration-200">
            <div className="h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500" />
            <CardHeader className="pb-4">
              <CardTitle className="font-heading text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/20">
                  <Package className="h-4 w-4" />
                </div>
                My Orders
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {orders.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="relative overflow-hidden rounded-3xl border-2 border-dashed border-indigo-200 dark:border-indigo-800/50 bg-gradient-to-br from-indigo-50/60 to-purple-50/40 dark:from-gray-900/80 dark:to-indigo-950/30 shadow-xl shadow-gray-200/50 dark:shadow-none"
                >
                  <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(99,102,241,0.15),transparent)] pointer-events-none" />
                  <div className="relative p-10 sm:p-14 text-center">
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg shadow-indigo-500/30 mb-6">
                      <Package className="h-10 w-10" />
                    </div>
                    <h3 className="font-heading text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-2">
                      No orders yet
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-8 max-w-sm mx-auto">
                      Your order history will appear here once you place your first order.
                    </p>
                    <Link href="/products">
                      <Button
                        size="lg"
                        className="rounded-xl font-semibold bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 hover:shadow-xl hover:shadow-indigo-500/30 text-white border-0 shadow-lg shadow-indigo-500/25 transition-all duration-200"
                      >
                        <ShoppingBag className="h-5 w-5 mr-2" />
                        Start Shopping
                      </Button>
                    </Link>
                  </div>
                </motion.div>
              ) : (
                <div className="space-y-3">
                  {orders.map((order, i) => {
                    const config = statusConfig[order.status] || {
                      label: order.status.replace(/_/g, " "),
                      className: "bg-gray-100 text-gray-800 dark:bg-gray-500/20 dark:text-gray-300 border-gray-200 dark:border-gray-600",
                    };
                    return (
                      <motion.div
                        key={order.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        whileHover={{ y: -2 }}
                      >
                        <Link href={`/orders/${order.id}`}>
                          <div className="group flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border-2 border-indigo-100 dark:border-indigo-900/40 bg-white dark:bg-gray-800/50 p-4 sm:p-5 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-600/50 hover:shadow-lg hover:shadow-indigo-500/10 transition-all duration-200">
                            <div className="flex-1 min-w-0">
                              <div className="flex flex-wrap items-center gap-2 mb-2">
                                <span className="font-heading font-bold text-gray-900 dark:text-white">
                                  #{order.id.slice(0, 8)}
                                </span>
                                <Badge
                                  variant="outline"
                                  className={`rounded-lg font-medium border ${config.className}`}
                                >
                                  {config.label}
                                </Badge>
                              </div>
                              <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
                                <span className="flex items-center gap-1.5 rounded-lg bg-gray-100 dark:bg-gray-700/50 px-2 py-1">
                                  {order.delivery_method === "store_pickup" ? (
                                    <Store className="h-3.5 w-3.5 text-indigo-500" />
                                  ) : (
                                    <MapPin className="h-3.5 w-3.5 text-indigo-500" />
                                  )}
                                  {order.delivery_method === "store_pickup" ? "Store Pickup" : "Home Delivery"}
                                </span>
                                <span className="flex items-center gap-1.5 rounded-lg bg-gray-100 dark:bg-gray-700/50 px-2 py-1">
                                  <Calendar className="h-3.5 w-3.5 text-indigo-500" />
                                  {new Date(order.created_at).toLocaleDateString(undefined, {
                                    day: "numeric",
                                    month: "short",
                                    year: "numeric",
                                  })}
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-3 shrink-0">
                              <span className="font-heading text-lg font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                                {formatPrice(order.total)}
                              </span>
                              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 group-hover:bg-indigo-200 dark:group-hover:bg-indigo-800/50 transition-colors">
                                <ChevronRight className="h-5 w-5" />
                              </div>
                            </div>
                          </div>
                        </Link>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
