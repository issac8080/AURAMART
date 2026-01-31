"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { motion, AnimatePresence } from "framer-motion";
import { Package, Store, Home, Check, Clock, Truck, ArrowLeft, X, Gift, Sparkles, RefreshCw, CheckCheck, Info } from "lucide-react";
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
  const [markingDelivered, setMarkingDelivered] = useState(false);
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

  const handleMarkDelivered = async () => {
    if (!confirm("Mark this order as delivered? (Demo purpose)\n\nThis will:\n✓ Change status to 'delivered'\n✓ Enable Return/Exchange option\n✓ Credit AuraPoints to wallet")) return;
    setMarkingDelivered(true);
    try {
      const res = await fetch(`${API}/orders/${orderId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "delivered" })
      });
      if (res.ok) {
        const updated = await res.json();
        setOrder(updated);
        
        // Preview AuraPoints
        try {
          const cashbackRes = await fetch(`${API}/wallet/preview-cashback?order_total=${updated.total}`);
          if (cashbackRes.ok) {
            const cashbackData = await cashbackRes.json();
            setCashbackInfo({
              amount: cashbackData.points_amount || cashbackData.cashback_amount,
              rate: cashbackData.points_rate || cashbackData.cashback_rate,
            });
          }
        } catch {}
        
        alert("✓ Order marked as delivered!\n✓ AuraPoints will be credited\n✓ Return option now available");
      } else {
        alert("Failed to update order status");
      }
    } catch {
      alert("Failed to update order status");
    } finally {
      setMarkingDelivered(false);
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

      {/* AuraPoints Info Banner */}
      {order.status !== "cancelled" && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/20 dark:to-blue-950/20 border border-purple-200 dark:border-purple-800 rounded-lg p-4"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
              <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-1">
                AuraPoints Rewards
              </h3>
              <div className="text-sm text-purple-700 dark:text-purple-300 space-y-1">
                <p>✓ Earn up to 5% AuraPoints when order is delivered</p>
                <p>✓ Points credited automatically to your wallet</p>
                <p>✓ Valid for 30 days from delivery</p>
                {(order.status === "delivered" || order.status === "picked_up") && (
                  <p className="font-medium text-emerald-600 dark:text-emerald-400 mt-2">
                    ✓ If you return this order, AuraPoints will be deducted from your wallet
                  </p>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

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
              <div className="space-y-2">
                {/* Demo: Mark as Delivered Button */}
                {order.status !== "cancelled" && order.status !== "delivered" && order.status !== "picked_up" && (
                  <Button
                    variant="default"
                    className="w-full mt-4 bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={handleMarkDelivered}
                    disabled={markingDelivered}
                  >
                    <CheckCheck className="h-4 w-4 mr-2" />
                    {markingDelivered ? "Marking..." : "Mark as Delivered (Demo)"}
                  </Button>
                )}
                
                {/* Return / Exchange Button */}
                {(order.status === "delivered" || order.status === "picked_up") && (
                  <Link href={`/returns/create?orderId=${order.id}`}>
                    <Button
                      variant="outline"
                      className="w-full border-blue-600 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950"
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Return / Exchange
                    </Button>
                  </Link>
                )}
                
                {/* Cancel Order Button */}
                {order.status !== "cancelled" && order.status !== "delivered" && order.status !== "picked_up" && (
                  <Button
                    variant="destructive"
                    className="w-full bg-red-600 hover:bg-red-700 text-white"
                    onClick={handleCancelOrder}
                    disabled={cancelling}
                  >
                    <X className="h-4 w-4 mr-2" />
                    {cancelling ? "Cancelling..." : "Cancel Order"}
                  </Button>
                )}
              </div>
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
