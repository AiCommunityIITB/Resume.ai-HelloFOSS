"use client";

import React from "react";
import { PinContainer } from "../ui/3d-pin";
import { useAuth } from "@/context/AuthContext";

export function AnimatedPinDemo() {
  const { isAuthenticated, isLoading } = useAuth();

  const getLink = () => {
    if (isLoading) return "#";
    return isAuthenticated ? "/resumes" : "/sign-in";
  };

  const getTitle = () => {
    if (isLoading) return "Loading...";
    return isAuthenticated ? "Manage Resumes" : "Sign In";
  };

  return (
    <PinContainer title={getTitle()} href={getLink()}>
      <div className="flex basis-full flex-col p-4 w-[15rem] h-[15rem] tracking-tight text-slate-100/50 sm:basis-1/2 sm:w-[20rem] sm:h-[20rem]">
        <h3 className="max-w-xs !pb-2 !m-0 font-bold text-2xl text-slate-100">
          Get Started
        </h3>
        <div className="text-base !m-0 !p-0 font-normal">
          <span className="text-slate-500 ">
            Get instant rating of your Resume
          </span>
        </div>
        <div className="flex flex-1 w-full h-[8rem] rounded-lg mt-4 bg-[url('/images/AI.jpeg')] bg-cover" />
      </div>
    </PinContainer>
  );
}
