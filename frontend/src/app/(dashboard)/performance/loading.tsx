import { Skeleton } from "@/components/ui/skeleton";

export default function PerformanceLoading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-44" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border p-6 space-y-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>
      <div className="rounded-lg border p-6 space-y-4">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-64 w-full" />
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-lg border p-6 space-y-4">
          <Skeleton className="h-5 w-28" />
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </div>
        <div className="rounded-lg border p-6 space-y-4">
          <Skeleton className="h-5 w-28" />
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
