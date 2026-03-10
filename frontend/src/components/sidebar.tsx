"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/theme-toggle";

const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/pipelines", label: "Pipelines" },
  { href: "/gallery", label: "Gallery" },
  { href: "/brands", label: "Brands" },
  { href: "/performance", label: "Performance" },
  { href: "/deployment", label: "Deployment" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    document.cookie = "adforge_api_key=; path=/; max-age=0";
    router.push("/login");
  }

  return (
    <aside className="flex h-screen w-52 flex-col bg-sidebar">
      <div className="px-4 py-6">
        <span className="font-display text-xl font-black tracking-wider text-sidebar-primary">
          ADFORGE
        </span>
        <p className="mt-1 text-[10px] uppercase tracking-[0.12em] text-sidebar-foreground">
          CREATIVE INFRASTRUCTURE
        </p>
      </div>
      <nav className="flex-1 space-y-3 px-4">
        {navItems.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block font-mono text-xs uppercase tracking-wider transition-colors",
                active
                  ? "border-l-2 border-sidebar-accent pl-3 text-sidebar-primary"
                  : "text-sidebar-foreground hover:text-sidebar-primary",
              )}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="space-y-3 px-4 py-4">
        <button
          onClick={handleLogout}
          className="font-mono text-xs uppercase tracking-wider text-sidebar-foreground hover:text-sidebar-primary transition-colors"
        >
          Logout
        </button>
        <div className="flex items-center justify-between">
          <ThemeToggle />
          <span className="font-mono text-[10px] text-sidebar-foreground/50">
            v0.1
          </span>
        </div>
      </div>
    </aside>
  );
}
