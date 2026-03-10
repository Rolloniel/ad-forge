import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("bg-muted", className)}
      {...props}
    >
      <span className="animate-cursor-blink text-muted-foreground font-mono text-sm">_</span>
    </div>
  );
}

export { Skeleton };
