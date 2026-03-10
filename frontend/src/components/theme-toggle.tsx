"use client";

import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const options = [
    { value: "light" as const, icon: Sun, label: "Light" },
    { value: "dark" as const, icon: Moon, label: "Dark" },
    { value: "system" as const, icon: Monitor, label: "System" },
  ];

  return (
    <div className="flex items-center gap-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => setTheme(opt.value)}
          title={opt.label}
          className={cn(
            "p-1.5 transition-colors",
            theme === opt.value
              ? "text-sidebar-primary"
              : "text-sidebar-foreground hover:text-sidebar-primary",
          )}
        >
          <opt.icon className="h-3 w-3" />
        </button>
      ))}
    </div>
  );
}
