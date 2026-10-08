"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EyeIcon, EyeOffIcon, XCircleIcon, Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useRouter, useSearchParams } from "next/navigation";
import api from "@/lib/api";

const ResetPasswordPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isVisible, setIsVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setError("Invalid or missing password reset token.");
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setIsLoading(true);
    setError("");
    setSuccessMessage("");

    try {
      const res = await api.post("/api/v1/auth/reset-password", { token, password });
      const data = res.data;

      if (data.success) {
        setSuccessMessage(data.message || "Password has been reset successfully.");
        toast.success(data.message || "Password has been reset successfully.");
        router.push("/sign-in");
      } else {
        setError(data.message || "Failed to reset password.");
      }
    } catch (error: any) {
      setError(error.response?.data?.message || "An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleVisibility = () => setIsVisible((prevState) => !prevState);

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
                <h2 className="text-3xl font-bold text-foreground">Reset Password</h2>
                <p className="text-center text-sm text-muted-foreground">
                  Enter your new password.
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
                  <Label htmlFor="password">New Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      name="password"
                      type={isVisible ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter your new password"
                      disabled={isLoading}
                      className="h-11 pr-10"
                    />
                    <button
                      className="absolute inset-y-0 right-0 flex h-full w-10 items-center justify-center rounded-r-md text-muted-foreground/80 hover:text-foreground"
                      type="button"
                      onClick={toggleVisibility}
                      aria-label={isVisible ? "Hide password" : "Show password"}
                      disabled={isLoading}
                      tabIndex={-1}
                    >
                      {isVisible ? (
                        <EyeOffIcon size={16} aria-hidden="true" />
                      ) : (
                        <EyeIcon size={16} aria-hidden="true" />
                      )}
                    </button>
                  </div>
                </motion.div>

                <motion.div
                  className="space-y-2"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.8, ease: "easeOut" }}
                >
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <div className="relative">
                    <Input
                      id="confirmPassword"
                      name="confirmPassword"
                      type={isVisible ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm your new password"
                      disabled={isLoading}
                      className="h-11 pr-10"
                    />
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.9, ease: "easeOut" }}
                >
                  <Button
                    type="submit"
                    variant="default"
                    disabled={isLoading || !token}
                    className="w-full h-11 gap-2 shadow-md hover:shadow-lg transition-all duration-200"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Resetting...
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="h-4 w-4" />
                        Reset Password
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

export default ResetPasswordPage;
