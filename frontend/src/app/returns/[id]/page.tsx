"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Package,
  Mail,
  Phone,
  Calendar,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const API = "/api";

const statusConfig: Record<string, { label: string; icon: any; color: string }> = {
  PENDING: { label: "Pending", icon: Clock, color: "bg-amber-500/15 text-amber-700" },
  MANUAL_REVIEW_PENDING: { label: "Under Review", icon: AlertTriangle, color: "bg-blue-500/15 text-blue-700" },
  AI_APPROVED: { label: "Approved", icon: CheckCircle, color: "bg-emerald-500/15 text-emerald-700" },
  AI_REJECTED: { label: "Rejected", icon: XCircle, color: "bg-red-500/15 text-red-700" },
  ADMIN_APPROVED: { label: "Approved", icon: CheckCircle, color: "bg-emerald-500/15 text-emerald-700" },
  ADMIN_REJECTED: { label: "Rejected", icon: XCircle, color: "bg-red-500/15 text-red-700" },
  PROCESSING: { label: "Processing", icon: Clock, color: "bg-purple-500/15 text-purple-700" },
  COMPLETED: { label: "Completed", icon: CheckCircle, color: "bg-emerald-500/15 text-emerald-700" },
  CANCELLED: { label: "Cancelled", icon: XCircle, color: "bg-gray-500/15 text-gray-700" },
};

export default function ReturnDetailsPage() {
  const params = useParams();
  const returnId = params?.id as string;

  const [returnData, setReturnData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadReturn() {
      try {
        const res = await fetch(`${API}/returns/${returnId}`);
        if (!res.ok) throw new Error("Return request not found");
        const data = await res.json();
        setReturnData(data);
      } catch (err: any) {
        setError(err.message || "Failed to load return details");
      } finally {
        setLoading(false);
      }
    }
    if (returnId) loadReturn();
  }, [returnId]);

  if (loading) {
    return (
      <div className="py-12 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full mx-auto" />
        <p className="mt-4 text-muted-foreground">Loading return details...</p>
      </div>
    );
  }

  if (error || !returnData) {
    return (
      <div className="py-12 text-center">
        <Package className="h-16 w-16 mx-auto text-muted-foreground/50 mb-4" />
        <p className="text-lg font-medium text-muted-foreground">{error || "Return request not found"}</p>
        <Link href="/profile">
          <Button className="mt-4">Back to Orders</Button>
        </Link>
      </div>
    );
  }

  const statusInfo = statusConfig[returnData.status] || statusConfig.PENDING;
  const StatusIcon = statusInfo.icon;

  return (
    <div className="py-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href={`/orders/${returnData.order_id}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Return Request Details</h1>
          <p className="text-muted-foreground">Request #{returnData.id}</p>
        </div>
      </div>

      {/* Status Card */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Status</CardTitle>
              <Badge className={statusInfo.color}>
                <StatusIcon className="h-3 w-3 mr-1" />
                {statusInfo.label}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            {returnData.ai_decision && (
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <StatusIcon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">AI Decision: {returnData.ai_decision}</p>
                    {returnData.ai_confidence && (
                      <p className="text-sm text-muted-foreground">
                        Confidence: {(returnData.ai_confidence * 100).toFixed(1)}%
                      </p>
                    )}
                    {returnData.ai_reason && (
                      <p className="text-sm mt-2 text-muted-foreground">{returnData.ai_reason}</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {returnData.admin_decision && (
              <div className="mt-4 p-4 bg-muted/50 rounded-lg">
                <p className="font-medium">Admin Decision: {returnData.admin_decision}</p>
                {returnData.admin_note && (
                  <p className="text-sm mt-2 text-muted-foreground">{returnData.admin_note}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Return Details */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Card>
          <CardHeader>
            <CardTitle>Return Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-start gap-3">
                <Package className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-sm text-muted-foreground">Order ID</p>
                  <Link href={`/orders/${returnData.order_id}`}>
                    <p className="font-medium hover:text-primary cursor-pointer">{returnData.order_id}</p>
                  </Link>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-sm text-muted-foreground">Issue Type</p>
                  <p className="font-medium">{returnData.damage_type.replace(/_/g, " ")}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-sm text-muted-foreground">Submitted</p>
                  <p className="font-medium">{new Date(returnData.created_at).toLocaleString()}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-sm text-muted-foreground">Last Updated</p>
                  <p className="font-medium">{new Date(returnData.updated_at).toLocaleString()}</p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t">
              <p className="text-sm text-muted-foreground mb-2">Description</p>
              <p className="text-sm">{returnData.description}</p>
            </div>

            {returnData.probable_cause && (
              <div className="pt-4 border-t">
                <p className="text-sm text-muted-foreground mb-2">Probable Cause</p>
                <Badge variant="outline">{returnData.probable_cause.replace(/_/g, " ")}</Badge>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* Contact Info */}
      {(returnData.customer_email || returnData.customer_phone) && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {returnData.customer_email && (
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm">{returnData.customer_email}</span>
                </div>
              )}
              {returnData.customer_phone && (
                <div className="flex items-center gap-3">
                  <Phone className="h-5 w-5 text-muted-foreground" />
                  <span className="text-sm">{returnData.customer_phone}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Media Files */}
      {returnData.media_files && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <Card>
            <CardHeader>
              <CardTitle>Uploaded Media</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {JSON.parse(returnData.media_files).map((file: any, index: number) => (
                  <div key={index} className="relative">
                    <img
                      src={`data:${file.mime_type};base64,${file.data}`}
                      alt={file.filename || `Media ${index + 1}`}
                      className="w-full h-24 object-cover rounded-lg"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
