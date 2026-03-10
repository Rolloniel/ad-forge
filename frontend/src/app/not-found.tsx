import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-6">
      <span className="font-display text-[120px] font-black leading-none text-muted-foreground/20">
        404
      </span>
      <p className="text-label text-muted-foreground">PAGE NOT FOUND</p>
      <Link
        href="/dashboard"
        className="mt-4 border border-primary bg-primary px-5 py-2 font-mono text-xs uppercase tracking-wider text-primary-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
