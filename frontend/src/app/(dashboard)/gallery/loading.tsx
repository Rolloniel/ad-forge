export default function GalleryLoading() {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="h-10 w-32">
        <span className="animate-cursor-blink font-mono text-muted-foreground">
          _
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-4 border border-border p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-9 w-[140px] border border-dashed border-border" />
        ))}
      </div>
      <span className="text-label text-muted-foreground">Loading outputs...</span>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="border border-border overflow-hidden">
            <div className="flex h-40 items-center justify-center bg-muted/30">
              <span className="animate-cursor-blink font-mono text-muted-foreground">
                _
              </span>
            </div>
            <div className="p-3">
              <span className="text-label text-muted-foreground">---</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
