"use client";

import { usePathname } from "next/navigation";
import Header from "./Header";

const navItems = [
    {
        name: "Resumes",
        link: "/resumes",
    },
];

export default function MainLayout({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const noHeaderPaths = ["/", "/sign-in", "/sign-up"];
    const showHeader = !noHeaderPaths.includes(pathname);


    return (
        <>
            {showHeader && <Header navItems={navItems} />}
            {children}
        </>
    );
}
