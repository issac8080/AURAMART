"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Upload, X, AlertCircle, CheckCircle, Loader2, Sparkles, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const API = "/api";

type DamageType =
  | "PHYSICAL"
  | "FUNCTIONAL"
  | "COSMETIC"
  | "PACKAGING"
  | "MISSING_PARTS"
  | "WRONG_ITEM"
  | "SIZE_ISSUE"
  | "COLOR_ISSUE"
  | "QUALITY_ISSUE"
  | "OTHER";

const damageTypes: { value: DamageType; label: string; description: string }[] = [
  { value: "PHYSICAL", label: "Physical Damage", description: "Cracks, dents, scratches" },
  { value: "FUNCTIONAL", label: "Not Working", description: "Product doesn't function" },
  { value: "COSMETIC", label: "Cosmetic Issue", description: "Color, finish problems" },
  { value: "WRONG_ITEM", label: "Wrong Item", description: "Received different product" },
  { value: "SIZE_ISSUE", label: "Size Issue", description: "Doesn't fit properly" },
  { value: "QUALITY_ISSUE", label: "Quality Issue", description: "Poor quality/defective" },
  { value: "OTHER", label: "Other", description: "Other issues" },
];

export default function CreateReturnPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const orderId = searchParams.get("orderId");

  const [order, setOrder] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const [damageType, setDamageType] = useState<DamageType>("PHYSICAL");
  const [description, setDescription] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [mediaFiles, setMediaFiles] = useState<Array<{ data: string; mime_type: string; filename: string }>>([]);

  useEffect(() => {
    async function loadOrder() {
      if (!orderId) {
        setError("Order ID is required");
        setLoading(false);
        return;
      }

      try {
        const res = await fetch(`${API}/orders/${orderId}`);
        if (!res.ok) throw new Error("Order not found");
        const data = await res.json();
        setOrder(data);
      } catch (err) {
        setError("Failed to load order details");
      } finally {
        setLoading(false);
      }
    }
    loadOrder();
  }, [orderId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    const newFiles: typeof mediaFiles = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.size > 5 * 1024 * 1024) {
        alert(`File ${file.name} is too large. Maximum size is 5MB.`);
        continue;
      }

      const reader = new FileReader();
      reader.onload = (event) => {
        const base64 = event.target?.result as string;
        newFiles.push({
          data: base64.split(",")[1], // Remove data:image/jpeg;base64, prefix
          mime_type: file.type,
          filename: file.name,
        });

        if (newFiles.length === files.length) {
          setMediaFiles([...mediaFiles, ...newFiles]);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const removeFile = (index: number) => {
    setMediaFiles(mediaFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (description.length < 10) {
      setError("Description must be at least 10 characters");
      return;
    }

    if (!customerEmail && !customerPhone) {
      setError("Please provide at least email or phone number for updates");
      return;
    }

    setSubmitting(true);

    try {
      const res = await fetch(`${API}/returns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: orderId,
          damage_type: damageType,
          description,
          category: order.items[0]?.product_category || "General",
          customer_email: customerEmail || undefined,
          customer_phone: customerPhone || undefined,
          media_base64: mediaFiles,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to submit return request");
      }

      const returnData = await res.json();
      setSuccess(true);
      
      setTimeout(() => {
        router.push(`/returns/${returnData.id}`);
      }, 2000);
    } catch (err: any) {
      setError(err.message || "Failed to submit return request");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-12 text-center">
        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
        <p className="mt-4 text-muted-foreground">Loading order details...</p>
      </div>
    );
  }

  if (error && !order) {
    return (
      <div className="py-12 text-center">
        <AlertCircle className="h-16 w-16 mx-auto text-red-500 mb-4" />
        <p className="text-lg font-medium text-red-600">{error}</p>
        <Link href="/profile">
          <Button className="mt-4">Back to Orders</Button>
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="py-12 text-center"
      >
        <CheckCircle className="h-16 w-16 mx-auto text-emerald-500 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Return Request Submitted!</h2>
        <p className="text-muted-foreground">Redirecting to return details...</p>
      </motion.div>
    );
  }

  return (
    <div className="py-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href={`/orders/${orderId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Request Return / Exchange</h1>
          <p className="text-muted-foreground">Order #{orderId}</p>
        </div>
      </div>

      {/* AuraPoints Warning */}
      <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-amber-900 dark:text-amber-100 mb-1">
              Important: AuraPoints Deduction
            </h3>
            <p className="text-sm text-amber-700 dark:text-amber-300">
              If your return is approved, any AuraPoints earned from this order will be deducted from your wallet. 
              This is to maintain fairness in our rewards program.
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Order Info */}
        <Card>
          <CardHeader>
            <CardTitle>Order Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Order ID:</span>
                <span className="font-medium">{order?.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status:</span>
                <Badge>{order?.status}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Items:</span>
                <span className="font-medium">{order?.items?.length || 0} item(s)</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Damage Type */}
        <Card>
          <CardHeader>
            <CardTitle>Issue Type</CardTitle>
            <CardDescription>Select the type of issue you're experiencing</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {damageTypes.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setDamageType(type.value)}
                  className={`p-4 rounded-lg border-2 text-left transition-all ${
                    damageType === type.value
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <div className="font-medium">{type.label}</div>
                  <div className="text-sm text-muted-foreground">{type.description}</div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Description */}
        <Card>
          <CardHeader>
            <CardTitle>Description</CardTitle>
            <CardDescription>Describe the issue in detail (minimum 10 characters)</CardDescription>
          </CardHeader>
          <CardContent>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full min-h-[120px] p-3 rounded-lg border border-border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Please describe the issue with your order..."
              required
            />
            <div className="text-sm text-muted-foreground mt-2">
              {description.length} / 10 characters minimum
            </div>
          </CardContent>
        </Card>

        {/* Contact Info */}
        <Card>
          <CardHeader>
            <CardTitle>Contact Information</CardTitle>
            <CardDescription>We'll use this to send you updates about your return</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <Input
                type="email"
                value={customerEmail}
                onChange={(e) => setCustomerEmail(e.target.value)}
                placeholder="your.email@example.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Phone Number</label>
              <Input
                type="tel"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                placeholder="+1 234 567 8900"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              * Provide at least one contact method
            </p>
          </CardContent>
        </Card>

        {/* Media Upload */}
        <Card>
          <CardHeader>
            <CardTitle>Photos / Videos (Optional)</CardTitle>
            <CardDescription>Upload images or videos of the issue (max 5MB per file)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-border rounded-lg cursor-pointer hover:border-primary transition-colors">
                <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                <span className="text-sm text-muted-foreground">Click to upload files</span>
                <input
                  type="file"
                  multiple
                  accept="image/*,video/*"
                  onChange={handleFileUpload}
                  className="hidden"
                />
              </label>

              {mediaFiles.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {mediaFiles.map((file, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={`data:${file.mime_type};base64,${file.data}`}
                        alt={file.filename}
                        className="w-full h-24 object-cover rounded-lg"
                      />
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className="absolute top-1 right-1 p-1 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="h-4 w-4" />
                      </button>
                      <div className="text-xs text-muted-foreground mt-1 truncate">
                        {file.filename}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Error Message */}
        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex gap-3">
          <Link href={`/orders/${orderId}`} className="flex-1">
            <Button type="button" variant="outline" className="w-full">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={submitting} className="flex-1">
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              "Submit Return Request"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
