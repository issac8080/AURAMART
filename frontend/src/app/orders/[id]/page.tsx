"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { motion, AnimatePresence } from "framer-motion";
import { Package, Store, Home, Check, Clock, Truck, ArrowLeft, X, Gift, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatPrice } from "@/lib/utils";
import { SpinWheel } from "@/components/SpinWheel";
import { useCart } from "@/app/providers";

const API = "/api";

type Order = {
  id: string;
  user_id: string;
  items: Array<{ product_id: string; product_name?: string; quantity: number; price: number; image_url?: string | null }>;
  total: number;
  delivery_method: string;
  status: string;
  delivery_address?: string;
  store_location?: string;
  qr_code?: string;
  created_at: string;
};

const statusConfig: Record<string, { label: string; icon: any; color: string }> = {
  pending: { label: "Pending", icon: Clock, color: "bg-amber-500/15 text-amber-700" },
  confirmed: { label: "Confirmed", icon: Check, color: "bg-blue-500/15 text-blue-700" },
  ready_for_pickup: { label: "Ready for Pickup", icon: Store, color: "bg-emerald-500/15 text-emerald-700" },
  out_for_delivery: { label: "Out for Delivery", icon: Truck, color: "bg-purple-500/15 text-purple-700" },
  delivered: { label: "Delivered", icon: Check, color: "bg-emerald-500/15 text-emerald-700" },
  picked_up: { label: "Picked Up", icon: Check, color: "bg-emerald-500/15 text-emerald-700" },
  cancelled: { label: "Cancelled", icon: Clock, color: "bg-red-500/15 text-red-700" },
};

export default function OrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { sessionId } = useCart();
  const orderId = params?.id as string;
  const showSpin = searchParams.get("spin") === "1";
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const [cashbackInfo, setCashbackInfo] = useState<{ amount: number; rate: string } | null>(null);
  const [spinOpen, setSpinOpen] = useState(false);

  useEffect(() => {
    async function loadOrder() {
      try {
        const res = await fetch(`${API}/orders/${orderId}`);
        const data = await res.json();
        setOrder(data);
        
        // Preview AuraPoints if order is completed
        if (data && (data.status === "delivered" || data.status === "picked_up")) {
          try {
            const cashbackRes = await fetch(`${API}/wallet/preview-cashback?order_total=${data.total}`);
            if (cashbackRes.ok) {
              const cashbackData = await cashbackRes.json();
              setCashbackInfo({
                amount: cashbackData.points_amount || cashbackData.cashback_amount,
                rate: cashbackData.points_rate || cashbackData.cashback_rate,
              });
            }
          } catch {}
        }
      } catch {
        setOrder(null);
      } finally {
        setLoading(false);
      }
    }
    if (orderId) loadOrder();
  }, [orderId]);

  useEffect(() => {
    if (showSpin && order && !loading) setSpinOpen(true);
  }, [showSpin, order, loading]);

  const closeSpin = () => {
    setSpinOpen(false);
    router.replace(`/orders/${orderId}`, { scroll: false });
  };

  const handleCancelOrder = async () => {
    if (!confirm("Are you sure you want to cancel this order?")) return;
    setCancelling(true);
    try {
      const res = await fetch(`${API}/orders/${orderId}/cancel`, { method: "POST" });
      if (res.ok) {
        const updated = await res.json();
        setOrder(updated);
        alert("Order cancelled successfully");
      } else {
        alert("Failed to cancel order");
      }
    } catch {
      alert("Failed to cancel order");
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="py-12 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto" />
        <p className="mt-4 text-muted-foreground">Loading order...</p>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="py-12 text-center">
        <Package className="h-16 w-16 mx-auto text-muted-foreground/50 mb-4" />
        <p className="text-lg font-medium text-muted-foreground">Order not found</p>
        <Link href="/profile">
          <Button className="mt-4">View All Orders</Button>
        </Link>
      </div>
    );
  }

  const statusInfo = statusConfig[order.status] || statusConfig.pending;
  const StatusIcon = statusInfo.icon;

  return (
    <>
    <div className="py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/profile">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Order Details</h1>
          <p className="text-muted-foreground">Order #{order.id}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Order Status</CardTitle>
                <Badge className={statusInfo.color}>
                  <StatusIcon className="h-3 w-3 mr-1" />
                  {statusInfo.label}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                {order.delivery_method === "store_pickup" ? (
                  <Store className="h-12 w-12 text-primary" />
                ) : (
                  <Home className="h-12 w-12 text-primary" />
                )}
                <div>
                  <p className="font-medium">
                    {order.delivery_method === "store_pickup" ? "Store Pickup" : "Home Delivery"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {order.delivery_method === "store_pickup"
                      ? order.store_location
                      : order.delivery_address}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {(order.status === "delivered" || order.status === "picked_up") && cashbackInfo && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card className="border-emerald-500/20 bg-emerald-500/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-emerald-600" />
                    AuraPoints Earned!
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="text-3xl font-bold text-emerald-600">
                      {formatPrice(cashbackInfo.amount)}
                    </p>
                    <p className="text-sm text-emerald-700 dark:text-emerald-400 mt-1">
                      {cashbackInfo.rate} AuraPoints credited to your wallet
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>Valid for 30 days</span>
                  </div>
                  <Link href="/wallet">
                    <Button variant="outline" className="w-full" size="sm">
                      <Sparkles className="h-4 w-4 mr-2" />
                      View Wallet
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {order.delivery_method === "store_pickup" && order.qr_code && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card className="border-primary/20 bg-primary/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Package className="h-5 w-5 text-primary" />
                    Pickup QR Code
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-center space-y-4">
                  <div className="inline-block p-6 bg-white rounded-xl shadow-lg">
                    <QRCodeSVG value={order.qr_code} size={200} level="H" />
                  </div>
                  <div>
                    <p className="font-medium">Show this QR code at the store</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Store staff will scan this to complete your pickup
                    </p>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-semibold text-muted-foreground">
                      Order ID (if scanner fails):
                    </div>
                    <div className="text-2xl font-bold font-mono bg-muted/50 rounded-lg p-3 tracking-wider">
                      {order.id}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Staff can manually enter this order ID
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground font-mono bg-muted/30 rounded p-2 break-all">
                    {order.qr_code}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Order Items</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {order.items.map((item, i) => (
                <div key={i} className="flex justify-between items-center py-2 border-b last:border-0">
                  <div>
                    <p className="font-medium">Product {item.product_id}</p>
                    <p className="text-sm text-muted-foreground">Quantity: {item.quantity}</p>
                  </div>
                  <p className="font-medium">{formatPrice(item.price * item.quantity)}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div>
          <Card className="sticky top-24">
            <CardHeader>
              <CardTitle>Order Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span>{formatPrice(order.total)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Delivery</span>
                  <span className="text-emerald-600 font-medium">FREE</span>
                </div>
              </div>
              <div className="border-t pt-4">
                <div className="flex justify-between font-bold text-lg">
                  <span>Total</span>
                  <span className="text-primary">{formatPrice(order.total)}</span>
                </div>
              </div>
              <div className="text-xs text-muted-foreground">
                <p>Order placed: {new Date(order.created_at).toLocaleString()}</p>
              </div>
              {order.status !== "cancelled" && order.status !== "delivered" && order.status !== "picked_up" && (
                <Button
                  variant="destructive"
                  className="w-full mt-4 bg-red-600 hover:bg-red-700 text-white"
                  onClick={handleCancelOrder}
                  disabled={cancelling}
                >
                  <X className="h-4 w-4 mr-2" />
                  {cancelling ? "Cancelling..." : "Cancel Order"}
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
    <AnimatePresence>
      {spinOpen && (
        <SpinWheel
          orderId={orderId}
          sessionId={sessionId}
          onClose={closeSpin}
          onDone={closeSpin}
        />
      )}
    </AnimatePresence>
    </>
  );
}
