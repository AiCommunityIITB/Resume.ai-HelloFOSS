"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

interface LoginState {
  status: 'loading' | 'success' | 'error';
  message: string;
}

const SsoCallbackPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loginState, setLoginState] = useState<LoginState>({
    status: 'loading',
    message: 'Processing SSO login...'
  });

  useEffect(() => {
    const accessid = searchParams.get("accessid");

    if (!accessid) {
      setLoginState({
        status: 'error',
        message: 'No access token received from SSO provider'
      });
      return;
    }

    const handleSsoLogin = async () => {
      try {
        setLoginState({
          status: 'loading',
          message: 'Verifying your credentials...'
        });

        const res = await api.post("/api/v1/auth/sso-login", { accessid });
        const data = res.data;

        if (data.success) {
          setLoginState({
            status: 'success',
            message: data.message || "Login successful!"
          });
          
          toast.success("Welcome back!");
          
          setTimeout(() => {
            router.push("/dashboard");
          }, 1500);
        } else {
          setLoginState({
            status: 'error',
            message: data.message || "SSO login failed"
          });
        }
      } catch (error: any) {
        const message = error.response?.data?.message || 
                        error.message || 
                        "An unexpected error occurred during SSO login.";
        
        setLoginState({
          status: 'error',
          message
        });
      }
    };

    handleSsoLogin();
  }, [searchParams, router]);

  const handleRetry = () => {
    router.push("/sign-in");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardContent className="p-8 text-center space-y-6">
          {loginState.status === 'loading' && (
            <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto" />
          )}
          {loginState.status === 'success' && (
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
          )}
          {loginState.status === 'error' && (
            <XCircle className="h-12 w-12 text-red-500 mx-auto" />
          )}
          
          <div className="space-y-2">
            <h1 className="text-2xl font-bold">
              {loginState.status === 'loading' && 'Processing Login'}
              {loginState.status === 'success' && 'Login Successful'}
              {loginState.status === 'error' && 'Login Failed'}
            </h1>
            <p className="text-muted-foreground">{loginState.message}</p>
          </div>

          {loginState.status === 'error' && (
            <div className="space-y-3">
              <Button onClick={handleRetry} className="w-full">
                Try Again
              </Button>
            </div>
          )}

          {loginState.status === 'success' && (
            <p className="text-sm text-muted-foreground">
              Redirecting to dashboard...
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SsoCallbackPage;
