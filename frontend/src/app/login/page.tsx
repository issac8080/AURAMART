"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sparkles, Mail, LogIn, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/app/providers";
import { sendOtp, verifyOtp } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState<"email" | "otp">("email");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const trimmed = email.trim().toLowerCase();
    if (!trimmed || !trimmed.includes("@")) {
      setError("Please enter a valid email.");
      return;
    }
    setLoading(true);
    try {
      await sendOtp(trimmed);
      setEmail(trimmed);
      setStep("otp");
      setOtp("");
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send OTP. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!otp.trim()) {
      setError("Enter the OTP from the terminal.");
      return;
    }
    setLoading(true);
    try {
      const data = await verifyOtp(email, otp);
      login(data.email, data.name);
      router.push("/profile");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid or expired OTP.");
    } finally {
      setLoading(false);
    }
  };

  const backToEmail = () => {
    setStep("email");
    setOtp("");
    setError("");
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <div className="rounded-3xl border-2 border-indigo-100 dark:border-indigo-900/40 bg-gradient-to-b from-white to-indigo-50/30 dark:from-gray-900/90 dark:to-indigo-950/20 shadow-2xl shadow-indigo-500/10 overflow-hidden">
          <div className="h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-500" />
          <div className="p-8 sm:p-10 space-y-8">
            <div className="text-center space-y-2">
              <Link href="/" className="inline-flex items-center gap-2 font-heading font-bold text-xl text-gray-900 dark:text-white hover:opacity-90">
                <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-500 to-blue-600 text-white shadow-lg shadow-indigo-500/30">
                  <Sparkles className="h-5 w-5" />
                </span>
                AuraShop
              </Link>
              <h1 className="font-heading text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white pt-2">
                {step === "email" ? "Login or Sign up" : "Enter OTP"}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {step === "email"
                  ? "Enter your email. We’ll show the OTP in the backend terminal."
                  : "Check the terminal where the backend is running and enter the 6-digit OTP."}
              </p>
            </div>

            {step === "email" ? (
              <form onSubmit={handleSendOtp} className="space-y-5">
                {error && (
                  <div className="rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/50 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                    {error}
                  </div>
                )}
                <div>
                  <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">Email</label>
                  <div className="relative mt-1.5">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pl-10 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
                      autoComplete="email"
                    />
                  </div>
                </div>
                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl h-12 font-semibold bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-600 hover:from-indigo-600 hover:via-purple-600 hover:to-blue-700 text-white shadow-lg shadow-indigo-500/30"
                >
                  {loading ? "Sending..." : "Send OTP"}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOtp} className="space-y-5">
                {error && (
                  <div className="rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/50 px-4 py-3 text-sm text-red-700 dark:text-red-300">
                    {error}
                  </div>
                )}
                <div className="rounded-xl bg-gray-100 dark:bg-gray-800/50 px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                  OTP sent to <strong className="text-gray-900 dark:text-white">{email}</strong>
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700 dark:text-gray-300">OTP (from terminal)</label>
                  <div className="relative mt-1.5">
                    <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <Input
                      type="text"
                      inputMode="numeric"
                      placeholder="123456"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      className="pl-10 rounded-xl border-2 border-gray-200 dark:border-gray-600 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-center text-lg tracking-[0.4em]"
                      maxLength={6}
                      autoComplete="one-time-code"
                    />
                  </div>
                </div>
                <Button
                  type="submit"
                  disabled={loading || otp.length < 6}
                  className="w-full rounded-xl h-12 font-semibold bg-gradient-to-r from-indigo-500 via-purple-500 to-blue-600 hover:from-indigo-600 hover:via-purple-600 hover:to-blue-700 text-white shadow-lg shadow-indigo-500/30"
                >
                  <LogIn className="h-5 w-5 mr-2" />
                  {loading ? "Verifying..." : "Verify & Login"}
                </Button>
                <Button type="button" variant="ghost" className="w-full rounded-xl" onClick={backToEmail}>
                  Use a different email
                </Button>
              </form>
            )}

            <p className="text-center text-xs text-gray-500 dark:text-gray-400">
              No password needed. OTP is shown in the backend terminal (run: <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">uvicorn app.main:app</code>).
            </p>
          </div>
        </div>

        <p className="text-center mt-6">
          <Link href="/" className="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline">
            ← Back to home
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
