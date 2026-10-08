"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider } from "@/context/AuthContext";
import { ResumeProvider } from "@/context/ResumeContext";

export function Providers({ children }: { children: React.ReactNode }) {
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

  if (!googleClientId) {
    // You can render a fallback or simply not render the provider
    return (
      <AuthProvider>
        <ResumeProvider>
          {children}
        </ResumeProvider>
      </AuthProvider>
    );
  }

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
      <AuthProvider>
        <ResumeProvider>
          {children}
        </ResumeProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}
