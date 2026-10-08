"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Loader2,
  ShieldCheck,
  XCircleIcon
} from "lucide-react";
import Link from "next/link";
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const VerifyOtpPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState("");
  const [otp, setOtp] = useState("");
  const [email, setEmail] = useState("");

  useEffect(() => {
    const emailFromQuery = searchParams.get("email");
    if (emailFromQuery) {
      setEmail(emailFromQuery);
    } else {
      // If no email is in the query, redirect to sign-up
      toast.error("No email provided for OTP verification.");
      router.push("/sign-up");
    }
  }, [searchParams, router]);

  const handleOtpChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = e.target;
    // Allow only digits and limit to 6 characters
    if (/^\d*$/.test(value) && value.length <= 6) {
      setOtp(value);
      setApiError("");
    }
  };

  const handleVerification = async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (otp.length !== 6) {
      setApiError("Please enter a 6-digit OTP.");
      return;
    }

    setIsLoading(true);
    setApiError("");

    try {
      const res = await api.post(`/api/v1/auth/verify-otp`, { email, otp });
      const data = res.data;

      if (data.success) {
        toast.success(data.message || "Verification successful! Welcome.");
        // The response from our new endpoint includes user and tokens
        const { user, tokens } = data.data;
        login(user, tokens); // Use the login function from AuthContext
        router.push("/resumes");
      } else {
        setApiError(data.message || "Verification failed");
      }
    } catch (error: any) {
      const message =
        error.response?.data?.message ||
        error.message ||
        "An unexpected error occurred during verification.";
      setApiError(message);
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
        >
          <Card className="w-full max-w-md border-border/70 bg-card/20 shadow-[0_10px_26px_#e0e0e0a1] backdrop-blur-lg dark:shadow-none">
            <CardContent className="space-y-6 p-8">
              <motion.div
                className="space-y-4 text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4, ease: "easeOut" }}
              >
                <div className="flex items-center justify-center space-x-2">
                  <ShieldCheck className="h-8 w-8 text-primary" />
                  <span className="text-2xl font-bold tracking-tight md:text-4xl">
                    Verify Your Email
                  </span>
                </div>
                <p className="text-center text-sm text-muted-foreground">
                  An OTP has been sent to <span className="font-medium text-primary">{email}</span>.
                </p>
              </motion.div>
              
              {apiError && (
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
                  <p className="leading-relaxed">{apiError}</p>
                </motion.div>
              )}

              <form onSubmit={handleVerification} className="space-y-6">
                <motion.div
                  className="space-y-2"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.7, ease: "easeOut" }}
                >
                  <Label htmlFor="otp" className="text-sm font-medium">
                    One-Time Password
                  </Label>
                  <Input
                    id="otp"
                    name="otp"
                    type="text"
                    value={otp}
                    onChange={handleOtpChange}
                    placeholder="Enter 6-digit OTP"
                    disabled={isLoading}
                    className="h-12 text-center text-lg tracking-[0.5em]"
                    maxLength={6}
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 1.0, ease: "easeOut" }}
                >
                  <Button
                    type="submit"
                    variant={"default"}
                    disabled={isLoading || otp.length !== 6}
                    className="w-full h-11 gap-2 transition cursor-pointer shadow-md hover:shadow-lg"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Verifying...
                      </>
                    ) : (
                      "Verify"
                    )}
                  </Button>
                </motion.div>
              </form>

              <motion.p
                className="text-center text-xs text-muted-foreground leading-relaxed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 1.1, ease: "easeOut" }}
              >
                Didn't receive an OTP?{" "}
                <Link
                  href="/sign-up"
                  className="text-muted-foreground underline hover:text-primary transition-colors"
                >
                  Go back to Sign Up
                </Link>
                .
              </motion.p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default VerifyOtpPage;
