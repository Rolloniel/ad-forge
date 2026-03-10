export default function PipelinesLoading() {
  return (
    <div className="animate-fade-in flex h-full gap-6">
      <div className="min-w-0 flex-1 space-y-6">
        <div className="h-10 w-36">
          <span className="animate-cursor-blink font-mono text-muted-foreground">
            _
          </span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="border border-border p-6 space-y-3">
              <span className="text-label text-muted-foreground">
                Pipeline
              </span>
              <div>
                <span className="animate-cursor-blink font-mono text-muted-foreground">
                  _
                </span>
              </div>
              <div className="h-3" />
              <div className="h-3" />
            </div>
          ))}
        </div>
      </div>
      <aside className="hidden w-72 shrink-0 space-y-4 lg:block">
        <span className="text-label text-muted-foreground">Recent Jobs</span>
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="border border-border p-3">
              <span className="animate-cursor-blink font-mono text-xs text-muted-foreground">
                _
              </span>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
