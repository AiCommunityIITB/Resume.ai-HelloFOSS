import "./globals.css";
import { Inter } from "next/font/google";
import { Providers } from "./providers";
import { AuthProvider } from "@/context/AuthContext";
import MainLayout from "@/components/MainLayout";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Resume Rater",
  description: "Rate and improve your resume intelligently.",
  icons: {
    icon: "/images/AIClogo.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-background text-foreground`}>
        <Providers>
          <MainLayout>{children}</MainLayout>
        </Providers>
      </body>
    </html>
  );
}
