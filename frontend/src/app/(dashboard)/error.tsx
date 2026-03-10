"use client";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 p-6">
      <div className="text-center">
        <span className="font-display text-[80px] font-black leading-none text-accent">
          ERR
        </span>
        <p className="mt-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Something went wrong
        </p>
      </div>
      <p className="max-w-md text-center font-mono text-sm text-muted-foreground">
        {error.message || "An unexpected error occurred."}
      </p>
      <button
        onClick={reset}
        className="border border-primary bg-primary px-5 py-2 font-mono text-xs uppercase tracking-wider text-primary-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        Try Again
      </button>
    </div>
  );
}
