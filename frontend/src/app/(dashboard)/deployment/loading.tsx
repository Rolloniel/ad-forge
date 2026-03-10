export default function DeploymentLoading() {
  return (
    <div className="animate-fade-in space-y-6">
      <div className="h-10 w-52">
        <span className="animate-cursor-blink font-mono text-muted-foreground">
          _
        </span>
      </div>
      <div className="flex gap-4 border-b border-border pb-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 w-24">
            <span className="text-label text-muted-foreground">---</span>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border border-border p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-label text-muted-foreground">
                Platform
              </span>
              <span className="animate-cursor-blink font-mono text-xs text-muted-foreground">
                _
              </span>
            </div>
            <div className="h-4" />
            <div className="h-4" />
            <div className="flex gap-2">
              <div className="h-8 w-20 border border-dashed border-border" />
              <div className="h-8 w-20 border border-dashed border-border" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
