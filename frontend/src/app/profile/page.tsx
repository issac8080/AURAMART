"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { User, Package, MapPin, Store, Edit, Mail, Phone, ChevronRight, Wallet, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useCart } from "@/app/providers";
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
  const userId = sessionId; // In production, use actual user ID
  const [profile, setProfile] = useState<Profile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  useEffect(() => {
    async function loadProfile() {
      try {
        const res = await fetch(`${API}/users/${userId}/profile`);
        if (res.ok) {
          const data = await res.json();
          setProfile(data);
          setName(data.name || "");
          setEmail(data.email || "");
          setPhone(data.phone || "");
        }
      } catch {}
    }
    async function loadOrders() {
      try {
        const res = await fetch(`${API}/users/${userId}/orders`);
        const data = await res.json();
        setOrders(data.orders || []);
      } catch {}
    }
    if (userId) {
      loadProfile();
      loadOrders();
    }
  }, [userId]);

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

  const statusColors: Record<string, string> = {
    pending: "bg-amber-500/15 text-amber-700",
    confirmed: "bg-blue-500/15 text-blue-700",
    ready_for_pickup: "bg-emerald-500/15 text-emerald-700",
    delivered: "bg-emerald-500/15 text-emerald-700",
    picked_up: "bg-emerald-500/15 text-emerald-700",
  };

  return (
    <div className="py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-fluid-2xl sm:text-fluid-3xl font-bold tracking-tight">My Profile</h1>
          <p className="text-muted-foreground">Manage your account and orders</p>
        </div>
        <div className="flex gap-2">
          <Link href="/wallet">
            <Button variant="outline">
              <Sparkles className="h-4 w-4 mr-2" />
              Aura Wallet
            </Button>
          </Link>
          <Link href="/checkout">
            <Button>
              <Package className="h-4 w-4 mr-2" />
              New Order
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Profile
                </CardTitle>
                {!editing && (
                  <Button variant="ghost" size="sm" onClick={() => setEditing(true)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {editing ? (
                <>
                  <div>
                    <label className="text-sm font-medium">Name</label>
                    <Input
                      placeholder="Your name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Email</label>
                    <Input
                      type="email"
                      placeholder="your@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium">Phone</label>
                    <Input
                      type="tel"
                      placeholder="Phone number"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleSaveProfile} className="flex-1">
                      Save
                    </Button>
                    <Button variant="outline" onClick={() => setEditing(false)} className="flex-1">
                      Cancel
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  {profile?.name && (
                    <div className="flex items-center gap-3">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span>{profile.name}</span>
                    </div>
                  )}
                  {profile?.email && (
                    <div className="flex items-center gap-3">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <span>{profile.email}</span>
                    </div>
                  )}
                  {profile?.phone && (
                    <div className="flex items-center gap-3">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <span>{profile.phone}</span>
                    </div>
                  )}
                  {!profile?.name && !profile?.email && !profile?.phone && (
                    <p className="text-sm text-muted-foreground">No profile information yet</p>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Package className="h-5 w-5" />
                Quick Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Orders</span>
                <span className="font-bold">{orders.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Completed</span>
                <span className="font-bold text-emerald-600">
                  {orders.filter((o) => o.status === "delivered" || o.status === "picked_up").length}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="md:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>My Orders</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {orders.length === 0 ? (
                <div className="text-center py-8">
                  <Package className="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
                  <p className="text-muted-foreground">No orders yet</p>
                  <Link href="/products">
                    <Button className="mt-4" size="sm">
                      Start Shopping
                    </Button>
                  </Link>
                </div>
              ) : (
                orders.map((order) => (
                  <motion.div
                    key={order.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <Link href={`/orders/${order.id}`}>
                      <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                        <CardContent className="p-4">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <p className="font-medium">#{order.id}</p>
                                <Badge className={statusColors[order.status] || "bg-muted"}>
                                  {order.status.replace("_", " ")}
                                </Badge>
                              </div>
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  {order.delivery_method === "store_pickup" ? (
                                    <Store className="h-3 w-3" />
                                  ) : (
                                    <MapPin className="h-3 w-3" />
                                  )}
                                  {order.delivery_method === "store_pickup" ? "Store Pickup" : "Home Delivery"}
                                </span>
                                <span>{new Date(order.created_at).toLocaleDateString()}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-4">
                              <p className="font-bold text-primary">{formatPrice(order.total)}</p>
                              <ChevronRight className="h-5 w-5 text-muted-foreground" />
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </Link>
                  </motion.div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
