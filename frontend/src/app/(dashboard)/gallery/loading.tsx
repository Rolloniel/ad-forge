import { Skeleton } from "@/components/ui/skeleton";

export default function GalleryLoading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      <div className="rounded-lg border p-4">
        <div className="flex flex-wrap items-end gap-4">
          <Skeleton className="h-9 w-[160px]" />
          <Skeleton className="h-9 w-[140px]" />
          <Skeleton className="h-9 w-[150px]" />
          <Skeleton className="h-9 w-[150px]" />
        </div>
      </div>
      <Skeleton className="h-4 w-24" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="rounded-lg border overflow-hidden">
            <Skeleton className="h-40 w-full rounded-none" />
            <div className="p-3 space-y-2">
              <div className="flex gap-1.5">
                <Skeleton className="h-5 w-14" />
                <Skeleton className="h-5 w-20" />
              </div>
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
