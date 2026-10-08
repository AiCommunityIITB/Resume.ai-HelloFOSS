"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  MailIcon, 
  XCircleIcon, 
  EyeIcon, 
  EyeOffIcon, 
  CheckIcon, 
  XIcon,
  Loader2,
  ShieldCheck
} from "lucide-react";
import Link from "next/link";
import React, { useState, useMemo, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import api from "@/lib/api";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/context/AuthContext";

interface RegisterData {
  name: string;
  email: string;
  password: string;
}

const SignUpPage = () => {
  const router = useRouter();
  const { isAuthenticated, isLoading: isAuthLoading, login } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isSsoLoading, setIsSsoLoading] = useState(false);
  const [apiError, setApiError] = useState("");
  const [registerData, setRegisterData] = useState<RegisterData>({
    name: "",
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

  const changeInputHandler = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setRegisterData({ ...registerData, [name]: value });
    setApiError("");
  };

  const toggleVisibility = () => setIsVisible((prevState) => !prevState);

  const checkStrength = (pass: string) => {
    const requirements = [
      { regex: /.{8,}/, text: "At least 8 characters" },
      { regex: /[0-9]/, text: "At least 1 number" },
      { regex: /[a-z]/, text: "At least 1 lowercase letter" },
      { regex: /[A-Z]/, text: "At least 1 uppercase letter" },
    ];

    return requirements.map((req) => ({
      met: req.regex.test(pass),
      text: req.text,
    }));
  };

  const strength = checkStrength(registerData.password);

  const strengthScore = useMemo(() => {
    return strength.filter((req) => req.met).length;
  }, [strength]);

  const getStrengthColor = (score: number) => {
    if (score === 0) return "bg-border";
    if (score <= 1) return "bg-red-500";
    if (score <= 2) return "bg-orange-500";
    if (score === 3) return "bg-amber-500";
    return "bg-emerald-500";
  };

  const getStrengthText = (score: number) => {
    if (score === 0) return "Enter a password";
    if (score <= 2) return "Weak password";
    if (score === 3) return "Medium password";
    return "Strong password";
  };

  const validateForm = (): boolean => {
    let isValid = true;

    // Sanitize inputs
    const sanitizedName = sanitizeInput(registerData.name);
    const sanitizedEmail = sanitizeInput(registerData.email);
    const sanitizedPassword = sanitizeInput(registerData.password);

    // Name validation
    if (!sanitizedName) {
      setApiError("Name is required");
      isValid = false;
    }
    // Email validation
    else if (!sanitizedEmail) {
      setApiError("Email is required");
      isValid = false;
    } else if (!isValidEmail(sanitizedEmail)) {
      setApiError("Please enter a valid email address");
      isValid = false;
    }
    // Password validation
    else if (!sanitizedPassword) {
      setApiError("Password is required");
      isValid = false;
    } else if (!isPasswordStrong(sanitizedPassword)) {
      setApiError("Password must be at least 8 characters long");
      isValid = false;
    }

    return isValid;
  };

  const handleRegistration = async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!validateForm()) return;

    setIsLoading(true);
    setApiError("");

    try {
      // Sanitize inputs before sending to API
      const sanitizedData = {
        name: sanitizeInput(registerData.name),
        email: sanitizeInput(registerData.email),
        password: sanitizeInput(registerData.password)
      };

      const res = await api.post(`/api/v1/auth/register`, sanitizedData);
      const data = res.data;

      if (data.success) {
        toast.success(data.message || "Registration successful! Please check your email for an OTP.");
        router.push(`/verify-otp?email=${encodeURIComponent(sanitizedData.email)}`);
      } else {
        setApiError(data.message || "Registration failed");
      }
    } catch (error: any) {
      const message =
        error.response?.data?.message ||
        error.message ||
        "An unexpected error occurred during registration.";
      setApiError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSsoLogin = () => {
    setIsSsoLoading(true);
    setApiError("");
    
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
        if (window.location.href.includes('/sign-up')) {
          setIsSsoLoading(false);
          setApiError("Failed to redirect to SSO login. Please try again.");
        }
      }, 3000);
      
      window.location.href = ssoUrl;
    } catch (error) {
      console.error('SSO redirect error:', error);
      setApiError(error instanceof Error ? error.message : "Failed to redirect to SSO login. Please try again.");
      setIsSsoLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      handleRegistration();
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
      <div className="absolute -top-10 left-0 h-1/2 w-full rounded-b-full bg-gradient-to-b from-background to-transparent blur"></div>
      <div className="absolute -top-64 left-0 h-1/2 w-full rounded-full bg-gradient-to-b from-primary/80 to-transparent blur-3xl"></div>
      <div className="relative z-10 grid min-h-screen grid-cols-1 md:grid-cols-2">
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
                alt="Illustration"
                className="md:w-90 rounded-2xl mx-auto h-auto w-full"
              />
            </motion.div>
          </div>
        </motion.div>

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
                    <span className="text-2xl font-bold tracking-tight md:text-4xl">
                      Sign Up
                    </span>
                  </div>
                  <p className="text-center text-sm text-muted-foreground">
                    Already have an account?{" "}
                    <Link
                      href="/sign-in"
                      className="font-medium text-primary hover:underline transition-colors"
                    >
                      Login
                    </Link>
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
                              login(data.data.user);
                              router.push('/resumes');
                            } else {
                              setApiError(data.message || 'Google login failed.');
                            }
                          } catch (error) {
                            setApiError('An error occurred during Google login.');
                          } finally {
                            setIsLoading(false);
                          }
                        }}
                        onError={() => {
                          setApiError('Google login failed. Please try again.');
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

                <form onSubmit={handleRegistration} className="space-y-4" onKeyPress={handleKeyPress}>
                  <motion.div
                    className="space-y-2"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.7, ease: "easeOut" }}
                  >
                    <Label htmlFor="name" className="text-sm font-medium">
                      Username
                    </Label>
                    <Input
                      id="name"
                      name="name"
                      type="text"
                      value={registerData.name}
                      onChange={changeInputHandler}
                      placeholder="Username"
                      disabled={isLoading || isSsoLoading}
                      className="h-11"
                    />
                  </motion.div>

                  <motion.div
                    className="space-y-2"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.8, ease: "easeOut" }}
                  >
                    <Label htmlFor="email" className="text-sm font-medium">
                      Email Address
                    </Label>
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      value={registerData.email}
                      onChange={changeInputHandler}
                      placeholder="m@example.com"
                      disabled={isLoading || isSsoLoading}
                      className="h-11"
                    />
                  </motion.div>

                  <motion.div
                    className="space-y-2"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.9, ease: "easeOut" }}
                  >
                    <Label htmlFor="password" className="text-sm font-medium">
                      Password
                    </Label>
                    <div className="relative">
                      <Input
                        id="password"
                        name="password"
                        placeholder="Password"
                        type={isVisible ? "text" : "password"}
                        value={registerData.password}
                        onChange={changeInputHandler}
                        disabled={isLoading || isSsoLoading}
                        className="h-11 pr-10"
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

                    {registerData.password.length > 0 && (
                      <>
                        <div
                          className="bg-border mt-3 mb-4 h-1 w-full overflow-hidden rounded-full"
                          role="progressbar"
                          aria-valuenow={strengthScore}
                          aria-valuemin={0}
                          aria-valuemax={4}
                          aria-label="Password strength"
                        >
                          <div
                            className={`h-full ${getStrengthColor(
                              strengthScore
                            )} transition-all duration-500 ease-out`}
                            style={{ width: `${(strengthScore / 4) * 100}%` }}
                          ></div>
                        </div>

                        <p
                          id={`description`}
                          className="text-foreground mb-2 text-sm font-medium"
                        >
                          {getStrengthText(strengthScore)}. Must contain:
                        </p>

                        <ul
                          className="space-y-1.5"
                          aria-label="Password requirements"
                        >
                          {strength.map((req, index) => (
                            <li key={index} className="flex items-center gap-2">
                              {req.met ? (
                                <CheckIcon
                                  size={16}
                                  className="text-emerald-500"
                                  aria-hidden="true"
                                />
                              ) : (
                                <XIcon
                                  size={16}
                                  className="text-muted-foreground/80"
                                  aria-hidden="true"
                                />
                              )}
                              <span
                                className={`text-xs ${
                                  req.met
                                    ? "text-emerald-600"
                                    : "text-muted-foreground"
                                }`}
                              >
                                {req.text}
                                <span className="sr-only">
                                  {req.met
                                    ? " - Requirement met"
                                    : " - Requirement not met"}
                                </span>
                              </span>
                            </li>
                          ))}
                        </ul>
                      </>
                    )}
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 1.0, ease: "easeOut" }}
                  >
                    <Button
                      type="submit"
                      variant={"default"}
                      disabled={isLoading || isSsoLoading}
                      className="w-full h-11 gap-2 transition cursor-pointer shadow-md hover:shadow-lg"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Creating Account...
                        </>
                      ) : (
                        <>
                          <MailIcon className="size-4" />
                          Continue with Email
                        </>
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
                  By signing up, you agree to our{" "}
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

export default SignUpPage;