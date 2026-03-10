export default function BrandsLoading() {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div className="h-10 w-28">
          <span className="animate-cursor-blink font-mono text-muted-foreground">
            _
          </span>
        </div>
        <div className="h-9 w-28 border border-border" />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="border border-border p-6 space-y-3">
            <span className="text-label text-muted-foreground">Brand</span>
            <div>
              <span className="animate-cursor-blink font-mono text-muted-foreground">
                _
              </span>
            </div>
            <div className="h-4" />
            <div className="flex gap-3">
              <span className="text-label text-muted-foreground">---</span>
              <span className="text-label text-muted-foreground">---</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
