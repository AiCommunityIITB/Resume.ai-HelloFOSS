"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  EyeIcon, 
  EyeOffIcon, 
  MailIcon, 
  XCircleIcon, 
  Loader2,
  ShieldCheck
} from "lucide-react";
import Link from "next/link";
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/context/AuthContext";

interface LoginData {
  email: string;
  password: string;
}

interface FormErrors {
  email: string;
  password: string;
  otp: string;
  api: string;
}

const SignInPage = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading: isAuthLoading, login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isSsoLoading, setIsSsoLoading] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({
    email: "",
    password: "",
    otp: "",
    api: ""
  });
  
  const [loginData, setLoginData] = useState<LoginData>({
    email: "",
    password: "",
  });

  const [isVisible, setIsVisible] = useState<boolean>(false);

  // Add input sanitization function
  const sanitizeInput = (input: string): string => {
    // Remove any HTML tags and trim whitespace
    return input.replace(/<[^>]*>/g, '').trim();
  };

  // Add email validation function
  const isValidEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Add password strength validation
  const isPasswordStrong = (password: string): boolean => {
    // At least 8 characters
    return password.length >= 8;
  };

  const clearError = (field: keyof FormErrors) => {
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: "" }));
    }
  };

  const clearAllErrors = () => {
    setErrors({ email: "", password: "", api: "" });
  };

  const changeInputHandler = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setLoginData({ ...loginData, [name]: value });
    clearError(name as keyof FormErrors);
    clearError('api');
  };

  const validateForm = (): boolean => {
    const newErrors: FormErrors = { email: "", password: "", api: "" };
    let isValid = true;

    // Sanitize inputs
    const sanitizedEmail = sanitizeInput(loginData.email);
    const sanitizedPassword = sanitizeInput(loginData.password);

    // Email validation
    if (!sanitizedEmail) {
      newErrors.email = "Email is required";
      isValid = false;
    } else if (!isValidEmail(sanitizedEmail)) {
      newErrors.email = "Please enter a valid email address";
      isValid = false;
    }

    // Password validation
    if (!sanitizedPassword) {
      newErrors.password = "Password is required";
      isValid = false;
    } else if (!isPasswordStrong(sanitizedPassword)) {
      newErrors.password = "Password must be at least 8 characters long";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleLogin = async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!validateForm()) return;

    setIsLoading(true);
    clearError('api');

    try {
      // Sanitize inputs before sending to API
      const sanitizedData = {
        email: sanitizeInput(loginData.email),
        password: sanitizeInput(loginData.password)
      };

      const res = await api.post(`/api/v1/auth/login`, sanitizedData);
      const data = res.data;

      if (data.success) {
        toast.success(data.message || "Login successful!");
        login(data.data.user, data.data.tokens);
        router.push("/resumes");
      } else {
        setErrors(prev => ({ 
          ...prev, 
          api: data.message || "Login failed. Please check your credentials." 
        }));
      }
    } catch (error: unknown) {
      let message = "An unexpected error occurred during login.";
      
      if (typeof error === 'object' && error !== null && 'response' in error) {
        const err = error as { response?: { data?: { message?: string }, status?: number }, code?: string };
        if (err.response?.data?.message) {
          message = err.response.data.message;
        } else if (err.response?.status === 401) {
          message = "Invalid email or password. Please try again.";
        } else if (err.response?.status === 429) {
          message = "Too many login attempts. Please try again later.";
        } else if (err.code === 'NETWORK_ERROR') {
          message = "Network error. Please check your connection.";
        }
      }
      
      setErrors(prev => ({ ...prev, api: message }));
    } finally {
      setIsLoading(false);
    }
  };


  const handleSsoLogin = () => {
    setIsSsoLoading(true);
    clearAllErrors();
    
    try {
      // Validate SSO project ID
      const ssoProjectId = process.env.NEXT_PUBLIC_SSO_PROJECT_ID;
      if (!ssoProjectId) {
        throw new Error("SSO Project ID is not configured");
      }
      
      // Construct SSO URL with proper validation
      const baseUrl = "https://sso.tech-iitb.org/project";
      const ssoUrl = `${baseUrl}/${encodeURIComponent(ssoProjectId)}/ssocall/`;
      
      // Validate URL format
      try {
        new URL(ssoUrl);
      } catch (urlError) {
        throw new Error("Invalid SSO URL configuration");
      }
      
      // Set a timeout to reset loading state if redirect fails
      setTimeout(() => {
        // If we're still on this page after 3 seconds, something went wrong
        if (window.location.href.includes('/sign-in')) {
          setIsSsoLoading(false);
          setErrors(prev => ({ 
            ...prev, 
            api: "Failed to redirect to SSO login. Please try again." 
          }));
        }
      }, 3000);
      
      window.location.href = ssoUrl;
    } catch (error) {
      console.error('SSO redirect error:', error);
      setErrors(prev => ({ 
        ...prev, 
        api: error instanceof Error ? error.message : "Failed to redirect to SSO login. Please try again." 
      }));
      setIsSsoLoading(false);
    }
  };

  const toggleVisibility = () => setIsVisible((prevState) => !prevState);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleLogin();
    }
  };

  useEffect(() => {
    if (!isAuthLoading && isAuthenticated) {
      router.push("/resumes");
    }
  }, [isAuthLoading, isAuthenticated, router]);

  if (isAuthLoading || isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="rose-gradient relative min-h-screen overflow-hidden bg-background">
      {/* Background gradients */}
      <div className="absolute -top-10 left-0 h-1/2 w-full rounded-b-full bg-gradient-to-b from-background to-transparent blur"></div>
      <div className="absolute -top-64 left-0 h-1/2 w-full rounded-full bg-gradient-to-b from-primary/80 to-transparent blur-3xl"></div>
      
      <div className="relative z-10 grid min-h-screen grid-cols-1 md:grid-cols-2">
        {/* Left side - Logo */}
        <motion.div
          className="hidden flex-1 items-center justify-center space-y-8 p-8 text-center md:flex"
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <div className="space-y-6">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            >
              <img
                src="/logo.png"
                alt="Application Logo"
                className="md:w-90 rounded-2xl mx-auto h-auto w-full max-w-md"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 24 24' fill='none' stroke='%23cccccc' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z'%3E%3C/path%3E%3Ccircle cx='12' cy='13' r='3'%3E%3C/circle%3E%3C/svg%3E";
                }}
              />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4, ease: "easeOut" }}
              className="text-center space-y-4"
            >
              <h2 className="text-3xl font-bold text-foreground">
                Welcome Back
              </h2>
              <p className="text-center text-sm text-muted-foreground">
                Access your account securely with your IIT Bombay credentials or email.
              </p>
            </motion.div>
          </div>
        </motion.div>

        {/* Right side - Login Form */}
        <motion.div
          className="flex flex-1 items-center justify-center p-8"
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
            className="w-full max-w-md"
          >
            <Card className="border-border/70 bg-card/20 shadow-[0_10px_26px_#e0e0e0a1] backdrop-blur-lg dark:shadow-none">
              <CardContent className="space-y-6 p-8">
                {/* Header */}
                <motion.div
                  className="space-y-4 text-center"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.4, ease: "easeOut" }}
                >
                  <div className="flex items-center justify-center space-x-2">
                    <span className="text-2xl font-bold tracking-tight md:text-4xl">
                      Sign In
                    </span>
                  </div>
                  <p className="text-center text-sm text-muted-foreground">
                    Don't have an account?{" "}
                    <Link
                      href="/sign-up"
                      className="font-medium text-primary hover:underline transition-colors"
                    >
                      Sign up
                    </Link>
                  </p>
                </motion.div>

                {/* API Error Display */}
                {errors.api && (
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
                    <p className="leading-relaxed">{errors.api}</p>
                  </motion.div>
                )}

                {/* SSO and Google Login Buttons */}
                <div className="space-y-4">
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.5, ease: "easeOut" }}
                  >
                    <Button
                      type="button"
                      className="w-full h-11 gap-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white border-0 shadow-md hover:shadow-lg transition-all duration-200"
                      onClick={handleSsoLogin}
                      disabled={isSsoLoading || isLoading}
                    >
                      {isSsoLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Redirecting to SSO...
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="h-5 w-5" />
                          Sign in with ITC SSO
                        </>
                      )}
                    </Button>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.5, ease: "easeOut" }}
                    className="w-full"
                  >
                    <div 
                      className="
                        w-full 
                        h-11 
                        flex 
                        items-center 
                        justify-center 
                        rounded-md 
                        overflow-hidden"
                    >
                      <GoogleLogin
                        onSuccess={async (credentialResponse) => {
                          setIsLoading(true);
                          try {
                            const res = await api.post('/api/v1/auth/google-login', {
                              token: credentialResponse.credential,
                            });
                            const data = res.data;
                            if (data.success) {
                              toast.success(data.message || 'Login successful!');
                              login(data.data.user, data.data.tokens);
                              router.push('/resumes');
                            } else {
                              setErrors((prev) => ({
                                ...prev,
                                api: data.message || 'Google login failed.',
                              }));
                            }
                          } catch (error) {
                            setErrors((prev) => ({
                              ...prev,
                              api: 'An error occurred during Google login.',
                            }));
                          } finally {
                            setIsLoading(false);
                          }
                        }}
                        onError={() => {
                          setErrors((prev) => ({
                            ...prev,
                            api: 'Google login failed. Please try again.',
                          }));
                        }}
                        theme="outline"
                        size="large"
                        shape="rectangular"
                        logo_alignment="center"
                        text="continue_with"
                        width="448"
                      />
                    </div>
                  </motion.div>
                </div>

                {/* Divider */}
                <motion.div
                  className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.6, ease: "easeOut" }}
                >
                  <span className="relative z-10 bg-background px-3 text-muted-foreground">
                    Or continue with email
                  </span>
                </motion.div>

                {/* Login Form */}
                <form onSubmit={handleLogin} className="space-y-4" onKeyPress={handleKeyPress}>
                  {/* Email Field */}
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
                      value={loginData.email}
                      onChange={changeInputHandler}
                      placeholder="name@example.com"
                      disabled={isLoading || isSsoLoading}
                      className={`h-11 ${errors.email ? "border-red-500 focus:border-red-500" : ""}`}
                      autoComplete="email"
                      aria-describedby={errors.email ? "email-error" : undefined}
                    />
                    {errors.email && (
                      <motion.p 
                        initial={{ opacity: 0, y: -5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-red-500 text-sm flex items-center gap-1"
                        id="email-error"
                      >
                        <XCircleIcon className="h-3 w-3" />
                        {errors.email}
                      </motion.p>
                    )}
                  </motion.div>

                  {/* Password Field */}
                  <motion.div
                    className="space-y-2"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.8, ease: "easeOut" }}
                  >
                    <Label htmlFor="password" className="text-sm font-medium">
                      Password
                    </Label>
                    <div className="relative">
                      <Input
                        id="password"
                        name="password"
                        placeholder="Enter your password"
                        type={isVisible ? "text" : "password"}
                        value={loginData.password}
                        onChange={changeInputHandler}
                        disabled={isLoading || isSsoLoading}
                        className={`h-11 pr-10 ${errors.password ? "border-red-500 focus:border-red-500" : ""}`}
                        autoComplete="current-password"
                        aria-describedby={errors.password ? "password-error" : undefined}
                      />
                      <button
                        className="absolute inset-y-0 right-0 flex h-full w-10 items-center justify-center rounded-r-md text-muted-foreground/80 hover:text-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
                        type="button"
                        onClick={toggleVisibility}
                        aria-label={isVisible ? "Hide password" : "Show password"}
                        disabled={isLoading || isSsoLoading}
                        tabIndex={-1}
                      >
                        {isVisible ? (
                          <EyeOffIcon size={16} aria-hidden="true" />
                        ) : (
                          <EyeIcon size={16} aria-hidden="true" />
                        )}
                      </button>
                    </div>
                    {errors.password && (
                      <motion.p 
                        initial={{ opacity: 0, y: -5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-red-500 text-sm flex items-center gap-1"
                        id="password-error"
                      >
                        <XCircleIcon className="h-3 w-3" />
                        {errors.password}
                      </motion.p>
                    )}
                  </motion.div>

                  {/* Login Button */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.9, ease: "easeOut" }}
                  >
                    <Button
                      type="submit"
                      variant="default"
                      disabled={isLoading || isSsoLoading}
                      className="w-full h-11 gap-2 shadow-md hover:shadow-lg transition-all duration-200"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Signing In...
                        </>
                      ) : (
                        <>
                          <MailIcon className="h-4 w-4" />
                          Continue with Email
                        </>
                      )}
                    </Button>
                  </motion.div>
                </form>

                {/* Forgot Password Link */}
                <motion.div
                  className="text-center"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 1.0, ease: "easeOut" }}
                >
                  <Link
                    href="/forgot-password"
                    className="text-sm text-muted-foreground hover:text-primary hover:underline transition-colors"
                  >
                    Forgot your password?
                  </Link>
                </motion.div>

                {/* Terms */}
                <motion.p
                  className="text-center text-xs text-muted-foreground leading-relaxed"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 1.1, ease: "easeOut" }}
                >
                  By signing in, you agree to our{" "}
                  <Link
                    href="/terms"
                    className="text-muted-foreground underline hover:text-primary transition-colors"
                  >
                    Terms of Service
                  </Link>{" "}
                  and{" "}
                  <Link
                    href="/privacy"
                    className="text-muted-foreground underline hover:text-primary transition-colors"
                  >
                    Privacy Policy
                  </Link>
                  .
                </motion.p>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default SignInPage;