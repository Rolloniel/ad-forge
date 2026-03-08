"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PlayCircle,
  ImageIcon,
  Palette,
  BarChart3,
  Rocket,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/pipelines", label: "Pipelines", icon: PlayCircle },
  { href: "/gallery", label: "Gallery", icon: ImageIcon },
  { href: "/brands", label: "Brands", icon: Palette },
  { href: "/performance", label: "Performance", icon: BarChart3 },
  { href: "/deployment", label: "Deployment", icon: Rocket },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-sidebar text-sidebar-foreground">
      <div className="flex h-14 items-center border-b px-4">
        <span className="text-lg font-semibold">AdForge</span>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-3">
        <ThemeToggle />
      </div>
    </aside>
  );
}
