"use client"
import React from "react";
import { ResumeProvider } from "@/context/ResumeContext";

const DashboardLayout = ({ children }: { children: React.ReactNode }) => {
  return <ResumeProvider>{children}</ResumeProvider>;
};

export default DashboardLayout;
