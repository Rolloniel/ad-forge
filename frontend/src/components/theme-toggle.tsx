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
    <div className="flex items-center gap-1 rounded-md border bg-muted/50 p-0.5">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => setTheme(opt.value)}
          title={opt.label}
          className={cn(
            "rounded-sm p-1.5 transition-colors",
            theme === opt.value
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          <opt.icon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  );
}
