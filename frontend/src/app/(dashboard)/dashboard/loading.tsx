export default function DashboardLoading() {
  return (
    <div className="animate-fade-in space-y-8">
      <div className="h-10 w-48">
        <span className="animate-cursor-blink font-mono text-muted-foreground">
          _
        </span>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border border-border p-6">
            <span className="text-label text-muted-foreground">Loading</span>
            <div className="mt-2">
              <span className="animate-cursor-blink font-mono text-2xl text-muted-foreground">
                _
              </span>
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="border border-border p-6">
            <span className="text-label text-muted-foreground">Loading</span>
            <div className="mt-4 h-48 border border-dashed border-border" />
          </div>
        ))}
      </div>
    </div>
  );
}
