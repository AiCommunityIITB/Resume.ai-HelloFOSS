"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import Cookies from 'js-cookie';
import api from '@/lib/api';
import { useRouter, usePathname } from 'next/navigation';
import { toast } from 'sonner';

interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  roll_number?: string | null;
  department?: string | null;
  degree?: string | null;
  passing_year?: number | null;
  is_sso_user: boolean;
  created_at: string;
  updated_at?: string | null;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (userData: User) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Function to validate user data
  const validateUserData = (userData: any): userData is User => {
    return (
      userData &&
      typeof userData === 'object' &&
      typeof userData.id === 'string' &&
      typeof userData.username === 'string' &&
      typeof userData.email === 'string' &&
      typeof userData.is_active === 'boolean' &&
      typeof userData.is_superuser === 'boolean' &&
      typeof userData.is_sso_user === 'boolean' &&
      typeof userData.created_at === 'string'
    );
  };

  // Function to sanitize user data
  const sanitizeUserData = (userData: any): User => {
    return {
      id: userData.id?.toString() || '',
      username: userData.username?.toString().substring(0, 100) || '',
      email: userData.email?.toString().toLowerCase().substring(0, 255) || '',
      is_active: Boolean(userData.is_active),
      is_superuser: Boolean(userData.is_superuser),
      roll_number: userData.roll_number ? userData.roll_number.toString().substring(0, 20) : null,
      department: userData.department ? userData.department.toString().substring(0, 100) : null,
      degree: userData.degree ? userData.degree.toString().substring(0, 50) : null,
      passing_year: userData.passing_year ? Number(userData.passing_year) : null,
      is_sso_user: Boolean(userData.is_sso_user),
      created_at: userData.created_at?.toString() || new Date().toISOString(),
      updated_at: userData.updated_at ? userData.updated_at.toString() : null
    };
  };

  useEffect(() => {
    const checkUser = async () => {
      // Skip authentication check for public routes
      const publicRoutes = ['/sign-in', '/sign-up', '/sso-callback', '/forgot-password'];
      if (publicRoutes.some(route => pathname.startsWith(route))) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await api.get('/api/v1/auth/me');
        if (response.data && response.data.data) {
          // Validate and sanitize user data
          if (validateUserData(response.data.data)) {
            const sanitizedUser = sanitizeUserData(response.data.data);
            setUser(sanitizedUser);
            setIsAuthenticated(true);
          } else {
            console.error("Invalid user data received from API");
            setIsAuthenticated(false);
            setUser(null);
          }
        } else {
          setIsAuthenticated(false);
          setUser(null);
        }
      } catch (error: any) {
        // The axios interceptor in api.ts handles token refresh.
        // If the refresh fails, the interceptor will redirect to /sign-in.
        // We just need to update the state here.
        console.error("Authentication check failed:", error.message);
        setIsAuthenticated(false);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };
    checkUser();
  }, [pathname, router]);

  const login = (userData: User) => {
    // Validate user data before setting state
    if (validateUserData(userData)) {
      const sanitizedUser = sanitizeUserData(userData);
      setUser(sanitizedUser);
      setIsAuthenticated(true);
    } else {
      console.error("Invalid user data provided to login function");
    }
  };

  const logout = async () => {
    try {
      await api.post('/api/v1/auth/logout');
      Cookies.remove('accessToken');
      Cookies.remove('refreshToken');
      setUser(null);
      setIsAuthenticated(false);
      router.push('/');
      toast.success("You have been logged out successfully.");
    } catch (error: any) {
      console.error('Logout failed', error);
      toast.error("Logout failed. Please try again.");
    }
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
