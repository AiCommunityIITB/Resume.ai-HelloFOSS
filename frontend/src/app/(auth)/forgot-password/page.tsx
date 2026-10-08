"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MailIcon, XCircleIcon, Loader2 } from "lucide-react";
import Link from "next/link";
import React, { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import api from "@/lib/api";

const ForgotPasswordPage = () => {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      const res = await api.post("/api/v1/auth/forgot-password", { email });
      const data = res.data;

      if (data.success) {
        setSuccessMessage(data.message || "If an account with this email exists, a password reset link has been sent.");
        toast.success(data.message || "If an account with this email exists, a password reset link has been sent.");
      } else {
        setError(data.message || "Failed to send password reset email.");
      }
    } catch (error: any) {
      setError(error.response?.data?.message || "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rose-gradient relative min-h-screen overflow-hidden bg-background">
      <div className="relative z-10 flex min-h-screen items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
          className="w-full max-w-md"
        >
          <Card className="border-border/70 bg-card/20 shadow-[0_10px_26px_#e0e0e0a1] backdrop-blur-lg dark:shadow-none">
            <CardContent className="space-y-6 p-8">
              <motion.div
                className="space-y-4 text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4, ease: "easeOut" }}
              >
                <h2 className="text-3xl font-bold text-foreground">Forgot Password</h2>
                <p className="text-center text-sm text-muted-foreground">
                  Enter your email to receive a password reset link.
                </p>
              </motion.div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                  className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 shadow-sm dark:border-red-800/50 dark:bg-red-900/10 dark:text-red-200"
                >
                  <XCircleIcon
                    className="h-5 w-5 mt-0.5 text-red-500 flex-shrink-0"
                    aria-hidden="true"
                  />
                  <p className="leading-relaxed">{error}</p>
                </motion.div>
              )}

              {successMessage && (
                <motion.div
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                  className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800 shadow-sm dark:border-green-800/50 dark:bg-green-900/10 dark:text-green-200"
                >
                  <p className="leading-relaxed">{successMessage}</p>
                </motion.div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <motion.div
                  className="space-y-2"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.7, ease: "easeOut" }}
                >
                  <Label htmlFor="email" className="text-sm font-medium">
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    disabled={isLoading}
                    className="h-11"
                    autoComplete="email"
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.9, ease: "easeOut" }}
                >
                  <Button
                    type="submit"
                    variant="default"
                    disabled={isLoading}
                    className="w-full h-11 gap-2 shadow-md hover:shadow-lg transition-all duration-200"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <MailIcon className="h-4 w-4" />
                        Send Reset Link
                      </>
                    )}
                  </Button>
                </motion.div>
              </form>

              <motion.div
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 1.0, ease: "easeOut" }}
              >
                <Link
                  href="/sign-in"
                  className="text-sm text-muted-foreground hover:text-primary hover:underline transition-colors"
                >
                  Back to Sign In
                </Link>
              </motion.div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
