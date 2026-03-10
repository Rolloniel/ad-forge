import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "flex min-h-[60px] w-full border-b border-input bg-transparent px-1 py-2 font-mono text-sm transition-all placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-b-2 focus-visible:border-ring aria-invalid:border-b-destructive disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
