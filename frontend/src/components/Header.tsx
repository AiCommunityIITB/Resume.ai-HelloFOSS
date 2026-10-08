"use client";
import Link from 'next/link';
import {
  Navbar,
  NavBody,
  NavItems,
  MobileNav,
  NavbarLogo,
  NavbarButton,
  MobileNavHeader,
  MobileNavToggle,
  MobileNavMenu,
} from "@/components/ui/resizable-navbar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useAuth } from '@/context/AuthContext';
import { useState } from "react";

interface NavItem {
    name: string;
    link: string;
}

interface HeaderProps {
    navItems?: NavItem[];
}

const Header = ({ navItems = [
    {
        name:"Home",
        link:"#Home",
    },
    {
        name: "About",
        link: "#About",
    },
    {
        name: "AI Model",
        link: "#Ai",
    },
    {
        name: "Contacts",
        link: "#contact",
    },
] }: HeaderProps) => {
    const { isAuthenticated, logout, isLoading, user } = useAuth();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    const handleLogout = () => {
        logout();
        setIsMobileMenuOpen(false);
    }

  return (
    <>
    <div className="fixed w-full my-8 z-100">
          <Navbar>
            {/* Desktop Navigation */}
            <NavBody>
              <NavbarLogo />
              <NavItems items={navItems} />
              <div className="flex items-center gap-4">
                {isLoading ? (
                  <NavbarButton variant="primary">Loading...</NavbarButton>
                ) : isAuthenticated ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                        <Avatar className="h-8 w-8">
                          <AvatarFallback>
                            {user?.username?.charAt(0).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-56" align="end">
                      <DropdownMenuLabel className="font-normal">
                        <div className="flex flex-col space-y-1">
                          <p className="text-sm font-medium leading-none">{user?.username}</p>
                          <p className="text-xs leading-none text-muted-foreground">
                            {user?.email}
                          </p>
                        </div>
                      </DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuGroup>
                        <Link href="/settings" passHref>
                          <DropdownMenuItem>
                            Profile
                          </DropdownMenuItem>
                        </Link>
                      </DropdownMenuGroup>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={handleLogout}>
                        Log out
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <NavbarButton href="/sign-in" variant="primary">Sign In</NavbarButton>
                )}
              </div>
            </NavBody>
     
            {/* Mobile Navigation */}
            <MobileNav>
              <MobileNavHeader>
                <NavbarLogo />
                <MobileNavToggle
                  isOpen={isMobileMenuOpen}
                  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                />
              </MobileNavHeader>
     
              <MobileNavMenu
                isOpen={isMobileMenuOpen}
                onClose={() => setIsMobileMenuOpen(false)}
              >
                {navItems.map((item, idx) => (
                  <a
                    key={`mobile-link-${idx}`}
                    href={item.link}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="relative text-neutral-600 dark:text-neutral-300"
                  >
                    <span className="block">{item.name}</span>
                  </a>
                ))}
                <div className="flex w-full flex-col gap-4">
                {isLoading ? (
                    <NavbarButton variant="primary" className="w-full">Loading...</NavbarButton>
                ) : isAuthenticated ? (
                    <>
                        <NavbarButton
                            href="/settings"
                            onClick={() => setIsMobileMenuOpen(false)}
                            variant="secondary"
                            className="w-full"
                        >
                            Profile
                        </NavbarButton>
                        <NavbarButton onClick={handleLogout} variant="primary" className="w-full">Logout</NavbarButton>
                    </>
                ) : (
                    <NavbarButton
                        href="/sign-in"
                        onClick={() => setIsMobileMenuOpen(false)}
                        variant="primary"
                        className="w-full"
                    >
                        Sign In
                    </NavbarButton>
                )}
                </div>
              </MobileNavMenu>
            </MobileNav>
          </Navbar>
    
        </div>
        </>
  )
}

export default Header
