# "Concrete & Steel" Frontend Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform AdForge's frontend from generic AI-dashboard aesthetics to an elegant minimal brutalist design ("Concrete & Steel") — warm concrete backgrounds, zero border-radius, hairline borders, monospace UI chrome, grotesque headings, single terracotta accent.

**Architecture:** Pure visual redesign. No structural changes to data flow, API calls, or state management. Changes target: CSS custom properties (globals.css), font imports (layout.tsx), shadcn/ui component overrides (components/ui/*.tsx), and page-level Tailwind classes (all page.tsx files). Existing component interfaces stay identical.

**Tech Stack:** Next.js 15, Tailwind CSS v4, shadcn/ui (Radix), Recharts, Google Fonts (Darker Grotesque + IBM Plex Mono)

**Design doc:** `docs/plans/2026-03-10-frontend-redesign-design.md`

---

## Task 1: Design Foundation — Fonts, Colors, Animations

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css`

### Step 1: Update font imports in layout.tsx

Replace Inter with Darker Grotesque (display) and IBM Plex Mono (body). Apply IBM Plex Mono as the default body font.

```tsx
// frontend/src/app/layout.tsx
import { Darker_Grotesque, IBM_Plex_Mono } from "next/font/google";

const darkerGrotesque = Darker_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["700", "800", "900"],
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});
```

Update the `<body>` className to use both font variables, with IBM Plex Mono as default:

```tsx
<body className={`${darkerGrotesque.variable} ${ibmPlexMono.variable} font-mono antialiased`}>
```

Remove the old `inter` import and usage entirely.

### Step 2: Replace all CSS custom properties in globals.css

Replace the entire `@theme inline` block and `.dark` block with the Concrete & Steel palette. Set `--radius: 0` globally.

**Light theme values:**

| Variable | Value |
|---|---|
| `--color-background` | `#F2F0ED` |
| `--color-foreground` | `#1A1A1A` |
| `--color-card` | `#FFFFFF` |
| `--color-card-foreground` | `#1A1A1A` |
| `--color-popover` | `#FFFFFF` |
| `--color-popover-foreground` | `#1A1A1A` |
| `--color-primary` | `#1A1A1A` |
| `--color-primary-foreground` | `#F2F0ED` |
| `--color-secondary` | `#E8E5E1` |
| `--color-secondary-foreground` | `#1A1A1A` |
| `--color-muted` | `#E8E5E1` |
| `--color-muted-foreground` | `#6B6560` |
| `--color-accent` | `#B04A32` |
| `--color-accent-foreground` | `#FFFFFF` |
| `--color-destructive` | `#8B3A3A` |
| `--color-destructive-foreground` | `#FFFFFF` |
| `--color-border` | `#D4D0CB` |
| `--color-input` | `#D4D0CB` |
| `--color-ring` | `#B04A32` |
| `--color-sidebar` | `#1A1A1A` |
| `--color-sidebar-foreground` | `#9B9590` |
| `--color-sidebar-primary` | `#F2F0ED` |
| `--color-sidebar-primary-foreground` | `#1A1A1A` |
| `--color-sidebar-accent` | `#B04A32` |
| `--color-sidebar-accent-foreground` | `#F2F0ED` |
| `--color-sidebar-border` | `#333333` |
| `--color-sidebar-ring` | `#B04A32` |
| `--radius` | `0` |

**Dark theme values (`.dark` class):**

| Variable | Value |
|---|---|
| `--color-background` | `#1A1A1A` |
| `--color-foreground` | `#F2F0ED` |
| `--color-card` | `#2A2725` |
| `--color-card-foreground` | `#F2F0ED` |
| `--color-popover` | `#2A2725` |
| `--color-popover-foreground` | `#F2F0ED` |
| `--color-primary` | `#F2F0ED` |
| `--color-primary-foreground` | `#1A1A1A` |
| `--color-secondary` | `#332F2C` |
| `--color-secondary-foreground` | `#F2F0ED` |
| `--color-muted` | `#332F2C` |
| `--color-muted-foreground` | `#9B9590` |
| `--color-accent` | `#B04A32` |
| `--color-accent-foreground` | `#FFFFFF` |
| `--color-destructive` | `#8B3A3A` |
| `--color-destructive-foreground` | `#F2F0ED` |
| `--color-border` | `#3A3735` |
| `--color-input` | `#3A3735` |
| `--color-ring` | `#B04A32` |
| `--color-sidebar` | `#111111` |
| `--color-sidebar-foreground` | `#9B9590` |
| `--color-sidebar-primary` | `#F2F0ED` |
| `--color-sidebar-primary-foreground` | `#1A1A1A` |
| `--color-sidebar-accent` | `#B04A32` |
| `--color-sidebar-accent-foreground` | `#F2F0ED` |
| `--color-sidebar-border` | `#2A2725` |
| `--color-sidebar-ring` | `#B04A32` |

### Step 3: Add custom theme tokens and utility classes

Add to `@theme inline`:

```css
--font-display: "Darker Grotesque", sans-serif;
--font-mono: "IBM Plex Mono", monospace;
--color-status-completed: #4A6B52;
--color-status-failed: #8B3A3A;
--color-status-running: #B04A32;
--color-status-pending: #9B9590;
```

Add after the `@layer base` block:

```css
/* Brutalist utility classes */
@layer utilities {
  .font-display {
    font-family: var(--font-display);
  }
  .text-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 500;
  }
  .text-page-title {
    font-family: var(--font-display);
    font-size: 32px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    line-height: 1.1;
  }
  .text-section-header {
    font-family: var(--font-display);
    font-size: 20px;
    font-weight: 700;
    line-height: 1.2;
  }
  .text-metric {
    font-family: var(--font-display);
    font-size: 36px;
    font-weight: 900;
    line-height: 1;
  }
}

/* Brutalist animations */
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes pulse-border {
  0%, 100% { border-left-color: var(--color-accent); }
  50% { border-left-color: transparent; }
}

@keyframes toast-progress {
  from { width: 100%; }
  to { width: 0%; }
}

.animate-cursor-blink {
  animation: cursor-blink 1s step-end infinite;
}

.animate-fade-in {
  animation: fade-in 200ms ease-out;
}

.animate-pulse-border {
  animation: pulse-border 2s ease-in-out infinite;
}

/* Stagger children animation */
.stagger-children > * {
  opacity: 0;
  animation: fade-in 200ms ease-out forwards;
}
.stagger-children > *:nth-child(1) { animation-delay: 0ms; }
.stagger-children > *:nth-child(2) { animation-delay: 50ms; }
.stagger-children > *:nth-child(3) { animation-delay: 100ms; }
.stagger-children > *:nth-child(4) { animation-delay: 150ms; }
.stagger-children > *:nth-child(5) { animation-delay: 200ms; }
.stagger-children > *:nth-child(6) { animation-delay: 250ms; }

/* Brutalist card hover — hard-edge offset shadow */
.brutalist-hover {
  transition: transform 120ms ease, box-shadow 120ms ease;
}
.brutalist-hover:hover {
  transform: translate(-2px, -2px);
  box-shadow: 4px 4px 0 var(--color-foreground);
}
```

### Step 4: Update Toaster in layout.tsx

Change Toaster to use the brutalist theme:

```tsx
<Toaster
  position="bottom-right"
  toastOptions={{
    unstyled: true,
    classNames: {
      toast: "bg-[#1A1A1A] text-[#F2F0ED] font-mono text-xs uppercase tracking-wider p-4 border border-[#333] flex items-center gap-3",
      title: "font-medium",
      description: "text-[#9B9590]",
    },
  }}
/>
```

### Step 5: Verify build

```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Step 6: Commit

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css
git commit -m "feat(frontend): add Concrete & Steel design foundation — fonts, colors, animations"
```

---

## Task 2: UI Component Overrides

Override all shadcn/ui components to match the brutalist aesthetic. Zero border-radius, monospace text, uppercase labels, no shadows.

**Files:**
- Modify: `frontend/src/components/ui/card.tsx`
- Modify: `frontend/src/components/ui/button.tsx`
- Modify: `frontend/src/components/ui/badge.tsx`
- Modify: `frontend/src/components/ui/input.tsx`
- Modify: `frontend/src/components/ui/textarea.tsx`
- Modify: `frontend/src/components/ui/table.tsx`
- Modify: `frontend/src/components/ui/dialog.tsx`
- Modify: `frontend/src/components/ui/select.tsx`
- Modify: `frontend/src/components/ui/label.tsx`
- Modify: `frontend/src/components/ui/skeleton.tsx`
- Modify: `frontend/src/components/ui/separator.tsx`
- Modify: `frontend/src/components/ui/accordion.tsx`

### Step 1: Override card.tsx

Card: white bg, 1px border, 0 radius, no shadow, 24px padding.

```tsx
// Card className:
"border border-border bg-card text-card-foreground"
// Remove: rounded-xl, shadow

// CardHeader: keep p-6 but change inner spacing
// CardTitle: keep as-is (pages will apply font-display class)
// CardContent: keep p-6 pt-0
```

Key changes:
- Card: remove `rounded-xl` and `shadow`, keep `border bg-card text-card-foreground`
- No other Card sub-component changes needed

### Step 2: Override button.tsx

```tsx
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-xs font-medium uppercase tracking-[0.08em] transition-colors duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-accent hover:text-accent-foreground",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-primary bg-transparent text-primary hover:bg-primary hover:text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:underline",
        link: "text-accent underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-5 py-2",
        sm: "h-8 px-3",
        lg: "h-10 px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);
```

Key changes: removed `rounded-md`, removed `shadow`/`shadow-sm`, added `uppercase tracking-[0.08em]`, changed `text-sm` to `text-xs`, hover on default goes to accent (terracotta), ghost uses `hover:underline` only.

### Step 3: Override badge.tsx

Rectangular, 1px border matching color, transparent bg, uppercase monospace.

```tsx
const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider whitespace-nowrap transition-colors [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        default: "border-primary/30 text-primary bg-transparent",
        secondary: "border-secondary-foreground/20 text-secondary-foreground bg-transparent",
        destructive: "border-destructive/50 text-destructive bg-transparent",
        outline: "border-border text-foreground bg-transparent",
        ghost: "border-transparent text-muted-foreground bg-transparent",
        link: "border-transparent text-accent underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);
```

Key changes: removed `rounded-full`, all variants are transparent bg with colored border/text only.

### Step 4: Override input.tsx

Bottom-border only by default, full border on focus.

```tsx
<input
  className={cn(
    "flex h-9 w-full border-b border-input bg-transparent px-1 py-1 font-mono text-sm transition-all placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-b-2 focus-visible:border-ring disabled:cursor-not-allowed disabled:opacity-50",
    className,
  )}
/>
```

Key changes: `border-b` only (not full border), removed `rounded-md`, removed `shadow-sm`, `px-1` instead of `px-3`, focus shows `border-b-2` with ring color (terracotta).

### Step 5: Override textarea.tsx

Same bottom-border treatment as input.

```tsx
<textarea
  className={cn(
    "flex min-h-[60px] w-full border-b border-input bg-transparent px-1 py-2 font-mono text-sm transition-all placeholder:text-muted-foreground focus-visible:outline-none focus-visible:border-b-2 focus-visible:border-ring disabled:cursor-not-allowed disabled:opacity-50",
    className,
  )}
/>
```

### Step 6: Override table.tsx

Full-width, no outer border, uppercase headers, hover rows.

```tsx
// TableHead className:
"h-10 px-3 text-left align-middle text-[11px] font-medium uppercase tracking-wider text-muted-foreground [&:has([role=checkbox])]:pr-0"

// TableRow className:
"border-b border-border transition-colors duration-75 hover:bg-[var(--color-secondary)] data-[state=selected]:bg-secondary"

// TableCell className:
"px-3 py-2.5 align-middle font-mono text-[13px] [&:has([role=checkbox])]:pr-0"
```

### Step 7: Override dialog.tsx

No blur overlay, 0 radius, generous padding.

```tsx
// DialogOverlay: change bg-black/50 to bg-[rgba(26,26,26,0.6)], remove backdrop-blur
"fixed inset-0 z-50 bg-[rgba(26,26,26,0.6)] data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0"

// DialogContent: remove rounded, add border, 32px padding
"fixed top-[50%] left-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border border-border bg-background p-8 duration-200 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95"

// DialogTitle: use font-display
"font-display text-lg font-bold uppercase tracking-wide leading-none"
```

### Step 8: Override select.tsx

Sharp rectangular dropdown, 0 radius.

```tsx
// SelectTrigger: remove rounded-md, use bottom-border style
"flex w-fit items-center justify-between gap-2 border-b border-input bg-transparent px-1 py-2 font-mono text-sm transition-all outline-none focus-visible:border-b-2 focus-visible:border-ring disabled:cursor-not-allowed disabled:opacity-50 data-[placeholder]:text-muted-foreground data-[size=default]:h-9 data-[size=sm]:h-8 ..."

// SelectContent: remove rounded-md
"relative z-50 ... overflow-y-auto border border-border bg-popover text-popover-foreground shadow-none ..."

// SelectItem: remove rounded-sm
"relative flex w-full cursor-default items-center gap-2 py-1.5 pr-8 pl-2 font-mono text-sm outline-hidden select-none focus:bg-secondary focus:text-secondary-foreground ..."
```

### Step 9: Override label.tsx

Uppercase monospace label style.

```tsx
"flex items-center gap-2 text-[11px] uppercase tracking-wider leading-none font-medium select-none text-muted-foreground group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50"
```

### Step 10: Override skeleton.tsx

Replace shimmer with blinking cursor.

```tsx
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("bg-muted", className)} {...props}>
      <span className="animate-cursor-blink text-muted-foreground font-mono text-sm">_</span>
    </div>
  );
}
```

### Step 11: Override separator.tsx

Ensure 1px hairline.

No changes needed — default separator is already `h-[1px] bg-border`.

### Step 12: Override accordion.tsx

Remove rounded corners if any, ensure clean borders.

### Step 13: Verify build

```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Step 14: Commit

```bash
git add frontend/src/components/ui/
git commit -m "feat(frontend): restyle all UI components for Concrete & Steel brutalist theme"
```

---

## Task 3: Sidebar, Shell & Theme Toggle

**Files:**
- Modify: `frontend/src/components/sidebar.tsx`
- Modify: `frontend/src/components/dashboard-shell.tsx`
- Modify: `frontend/src/components/theme-toggle.tsx`

### Step 1: Redesign sidebar.tsx

Replace icon-based nav with text-only, expanded sidebar (~200px). Remove all Lucide icon imports from sidebar.

```tsx
const navItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/pipelines", label: "Pipelines" },
  { href: "/gallery", label: "Gallery" },
  { href: "/brands", label: "Brands" },
  { href: "/performance", label: "Performance" },
  { href: "/deployment", label: "Deployment" },
];
```

Sidebar JSX structure:
- `<aside>` with `flex h-screen w-52 flex-col bg-sidebar`
- Logo section: `"ADFORGE"` in `font-display text-xl font-black tracking-wider text-sidebar-primary` + `"CREATIVE INFRASTRUCTURE"` subtitle in `text-[10px] uppercase tracking-[0.12em] text-sidebar-foreground mt-1`
- Nav items: `font-mono text-xs uppercase tracking-wider` with `text-sidebar-foreground` default, active state gets `text-sidebar-primary border-l-2 border-sidebar-accent pl-3`, hover gets `text-sidebar-primary`
- 12px vertical gap (`space-y-3`) between items
- Bottom section: ThemeToggle + `<span className="font-mono text-[10px] text-sidebar-foreground/50">v0.1</span>`
- No icons anywhere in nav

### Step 2: Update dashboard-shell.tsx

- Desktop sidebar stays hidden on mobile with `hidden md:block`
- Mobile overlay: change `bg-background/80 backdrop-blur-sm` to `bg-[rgba(26,26,26,0.6)]` (no blur)
- Mobile header: replace Button with ghost variant, change "AdForge" to uppercase font-display
- Main content: change `p-6` to `px-12 py-8 max-w-[1200px] mx-auto`

### Step 3: Update theme-toggle.tsx

Keep the 3-button toggle but restyle:
- Remove `rounded-md border bg-muted/50` wrapper → use `flex items-center gap-2`
- Active button: `text-sidebar-primary` (or `text-foreground` outside sidebar context)
- Inactive: `text-sidebar-foreground hover:text-sidebar-primary`
- Remove `rounded-sm` from individual buttons
- Keep icons but at `h-3 w-3`

### Step 4: Verify build

```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Step 5: Commit

```bash
git add frontend/src/components/sidebar.tsx frontend/src/components/dashboard-shell.tsx frontend/src/components/theme-toggle.tsx
git commit -m "feat(frontend): redesign sidebar, shell, and theme toggle for brutalist layout"
```

---

## Task 4: Login Page

**Files:**
- Modify: `frontend/src/app/login/page.tsx`

### Step 1: Redesign login page

Remove Card wrapper entirely. Center content on concrete background.

Structure:
```
<div centered on screen, bg-background>
  <div max-w-sm text-center>
    "ADFORGE" — text-page-title
    "CREATIVE INFRASTRUCTURE" — text-label text-muted-foreground mt-2
    <form mt-12 space-y-6>
      <Input type="password" bottom-border-only />
      {error && <p>...</p>}
      <Button full-width>SIGN IN</Button>
    </form>
  </div>
</div>
```

Remove Card, CardHeader, CardTitle, CardDescription, CardContent imports.

### Step 2: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/login/page.tsx
git commit -m "feat(frontend): redesign login page — minimal brutalist centered form"
```

---

## Task 5: Dashboard Page

**Files:**
- Modify: `frontend/src/app/(dashboard)/dashboard/page.tsx`

### Step 1: Redesign page header and KPI cards

- Page title: `<h1 className="text-page-title">DASHBOARD</h1>` — remove the `<p>` subtitle
- KPI cards: use `text-label` for card titles (11px uppercase mono), `text-metric` for values (36px Darker Grotesque), remove icons from cards
- Wrap KPI grid in `stagger-children` class
- Add `animate-fade-in` to the page wrapper

### Step 2: Redesign system status

Replace 3 StatusIndicator Card components with inline text items:

```tsx
<div className="flex items-center gap-8">
  {/* Each status: dot + label + status text */}
  <div className="flex items-center gap-2">
    <span className="h-2 w-2 bg-status-completed" /> {/* square dot, no rounded-full */}
    <span className="text-label">API Server</span>
    <span className="font-mono text-xs text-muted-foreground">Operational</span>
  </div>
  ...
</div>
```

### Step 3: Redesign quick launch

Replace Card wrapper with plain section. Buttons use `variant="outline"` (now brutalist style). Remove PlayCircle icons.

### Step 4: Redesign recent runs table

Remove Card wrapper around table. Use section header `"RECENT RUNS"` in `text-section-header` with a bottom border, then table directly.

Replace the `statusBadge` function to use the new Badge component with status-specific border colors:

```tsx
function statusBadge(status: Job["status"]) {
  const config: Record<string, { label: string; color: string }> = {
    completed: { label: "COMPLETED", color: "border-[var(--color-status-completed)] text-[var(--color-status-completed)]" },
    running: { label: "RUNNING", color: "border-[var(--color-status-running)] text-[var(--color-status-running)]" },
    failed: { label: "FAILED", color: "border-[var(--color-status-failed)] text-[var(--color-status-failed)]" },
    pending: { label: "PENDING", color: "border-[var(--color-status-pending)] text-[var(--color-status-pending)]" },
  };
  const { label, color } = config[status] ?? config.pending;
  return <Badge variant="outline" className={color}>{label}</Badge>;
}
```

Remove all Lucide icon imports that are no longer used (Activity, CheckCircle2, Clock, ImageIcon, Layers, Palette, PlayCircle, XCircle). Keep only Loader2.

### Step 5: Loading state

Replace Loader2 spinner with blinking cursor: `<span className="animate-cursor-blink font-mono">_</span>`

### Step 6: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/(dashboard)/dashboard/page.tsx
git commit -m "feat(frontend): redesign dashboard page — brutalist KPIs, status, and table"
```

---

## Task 6: Pipelines Page

**Files:**
- Modify: `frontend/src/app/(dashboard)/pipelines/page.tsx`

### Step 1: Redesign page header

Use `text-page-title` for "PIPELINES" / pipeline label. Remove subtitle `<p>` tags.

### Step 2: Redesign pipeline selection cards

- Remove icon imports (Video, Image, FileText, Globe, Type, RefreshCw) and icon rendering from PIPELINES array
- Cards: remove `hover:shadow-md` and `hover:border-primary/50`, add `brutalist-hover cursor-pointer`
- Remove the rounded icon box (`bg-primary/10 rounded-lg`), just show the label
- Pipeline name in `text-section-header`, description in regular mono text
- Step count: `"N STEPS"` in `text-label text-muted-foreground`
- Selected state: `bg-primary text-primary-foreground` (black fill, light text)

### Step 3: Redesign configure phase

- Toggle chips: change `rounded-full` to no rounding, change active style from `bg-primary` pill to `bg-primary text-primary-foreground border-primary` rectangle
- Pipeline steps preview: keep arrow flow but style in `text-label`
- Launch button: standard `variant="default"` (now brutalist)
- Remove Card wrapper, use section with border-bottom separators

### Step 4: Redesign running phase

- Step timeline: replace circle/check/x icons with text-based status
  - Completed: step name gets `line-through` decoration, text-muted-foreground
  - Running: terracotta left border that pulses (`animate-pulse-border border-l-2 pl-3`), normal text
  - Failed: `text-destructive`
  - Pending: `text-muted-foreground/40`
- Remove StepIcon component
- Connected line: `border-l border-border` (already CSS)
- "Live" indicator: keep small dot but use `bg-status-running` instead of `bg-green-500`

### Step 5: Redesign job history sidebar

- `<h2>` in `text-label` style
- Job cards: `brutalist-hover` on hover, remove `hover:bg-accent/50`
- Active card: `border-accent` left border
- StatusBadge: use new status badge pattern

### Step 6: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/(dashboard)/pipelines/page.tsx
git commit -m "feat(frontend): redesign pipelines page — brutalist cards, timeline, and config"
```

---

## Task 7: Brands Page

**Files:**
- Modify: `frontend/src/app/(dashboard)/brands/page.tsx`

### Step 1: Redesign brand cards

- Brand name: `text-section-header font-display`
- Voice text: `font-mono text-[13px] text-muted-foreground line-clamp-2`
- Product/audience counts: replace Badge components with plain text `"3 PRODUCTS · 2 AUDIENCES"` in `text-label text-muted-foreground`
- Remove Package and Users icon imports
- Cards: add `brutalist-hover cursor-pointer`
- Edit button: keep ghost variant, it now shows as underline-on-hover

### Step 2: Redesign empty state

- Remove Card wrapper and Megaphone icon
- Just centered text: `"NO BRANDS YET"` in `text-label text-muted-foreground` + Button below

### Step 3: Redesign dialog form

- Dialog uses updated component (0 radius, no blur)
- Section separators: keep Separator components
- Product/audience card-within-card: remove inner Card wrapper, use `border-b border-border py-4` dividers instead
- Product number label: `text-label`

### Step 4: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/(dashboard)/brands/page.tsx
git commit -m "feat(frontend): redesign brands page — brutalist cards and form dialog"
```

---

## Task 8: Gallery Page

**Files:**
- Modify: `frontend/src/app/(dashboard)/gallery/page.tsx`

### Step 1: Redesign filter bar

- Remove Card wrapper around filters
- Inline selects with the brutalist bottom-border style (handled by select override)
- "CLEAR" button: ghost variant (now just text with underline hover)
- Labels in `text-label`

### Step 2: Redesign output cards

- Remove `hover:shadow-md`, add `brutalist-hover`
- Remove `rounded` from image/video wrappers
- Badges: use new rectangular badge style
- Hover overlays (checkbox, download): keep but remove `rounded-md` and `backdrop-blur-sm`

### Step 3: Redesign preview dialog

- Uses updated dialog (0 radius, no blur overlay)
- Metadata panel: key-value pairs in `text-label` for keys, mono for values
- Remove `rounded-lg` from preview image/video/iframe

### Step 4: Redesign batch select bar

When items selected, show count in header area with `text-label` style.

### Step 5: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/(dashboard)/gallery/page.tsx
git commit -m "feat(frontend): redesign gallery page — brutalist grid, filters, and preview"
```

---

## Task 9: Performance Page

**Files:**
- Modify: `frontend/src/app/(dashboard)/performance/page.tsx`

### Step 1: Redesign KPI row

- Remove Card wrappers from KPI cards
- Instead: `flex items-center gap-8`, each KPI is a `div` with `text-label` title and `text-metric` value
- Separate KPIs with thin vertical hairlines: `border-r border-border last:border-r-0`
- Remove icon imports (Eye, MousePointerClick, Target, TrendingUp, DollarSign, BarChart3)

### Step 2: Redesign charts

Update Recharts theming:
- Bar fill: `#B04A32` (terracotta) for primary
- Line stroke: `#1A1A1A` for primary (or `#F2F0ED` in dark mode — use CSS variable)
- Grid lines: `#D4D0CB`
- No gradient fills
- Chart tooltip: remove `borderRadius`, set background to `var(--color-card)`, border `1px solid var(--color-border)`
- Bar radius: `[0, 0, 0, 0]` (no rounded tops)

### Step 3: Redesign insights section

- Each insight: replace `rounded-lg border p-4` with `border-l-2 border-accent pl-4 py-3` (blockquote style)
- Remove surrounding Card wrapper if desired, or keep but with updated card style
- ConfidenceBadge: use new badge variant

### Step 4: Redesign top hooks and patterns

- Hook ranking numbers: `bg-primary text-primary-foreground h-7 w-7` (square, not rounded)
- Pattern winner/loser badges: use new badge variant with status colors

### Step 5: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/(dashboard)/performance/page.tsx
git commit -m "feat(frontend): redesign performance page — brutalist KPIs, charts, and insights"
```

---

## Task 10: Deployment Page

**Files:**
- Modify: `frontend/src/app/(dashboard)/deployment/page.tsx`

### Step 1: Redesign tab navigation

Replace the pill-style tabs with text-based tabs:

```tsx
<div className="flex gap-6 border-b border-border">
  {tabs.map((tab) => (
    <button
      key={tab.key}
      onClick={() => setActiveTab(tab.key)}
      className={cn(
        "pb-2 font-mono text-xs uppercase tracking-wider transition-colors",
        activeTab === tab.key
          ? "border-b-2 border-accent text-foreground"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {tab.label}
    </button>
  ))}
</div>
```

Remove tab icons. Remove the wrapping `rounded-lg border bg-muted/50 p-1`.

### Step 2: Redesign campaign tree

- CampaignTreeNode: connector lines via `border-l border-border`, no accordion
- Badge type labels: use new rectangular badge
- PlatformBadge: rectangular, use new badge with platform-colored border

### Step 3: Redesign JSON viewer

```tsx
// JsonViewer pre:
"max-h-80 overflow-auto border border-border bg-[#F7F5F2] p-4 font-mono text-xs leading-relaxed"
// Dark mode: bg-[#1A1816]

// Syntax highlighting colors:
// Keys: text-foreground (black)
// Strings: text-muted-foreground (gray)
// Numbers/booleans: text-accent (terracotta)
// Punctuation: text-muted-foreground/50
```

Update `highlightJson` function color classes.

### Step 4: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/(dashboard)/deployment/page.tsx
git commit -m "feat(frontend): redesign deployment page — brutalist tabs, tree, and JSON viewer"
```

---

## Task 11: Loading States, 404, Error Page

**Files:**
- Modify: `frontend/src/app/(dashboard)/dashboard/loading.tsx`
- Modify: `frontend/src/app/(dashboard)/pipelines/loading.tsx`
- Modify: `frontend/src/app/(dashboard)/brands/loading.tsx`
- Modify: `frontend/src/app/(dashboard)/gallery/loading.tsx`
- Modify: `frontend/src/app/(dashboard)/performance/loading.tsx`
- Modify: `frontend/src/app/(dashboard)/deployment/loading.tsx`
- Modify: `frontend/src/app/not-found.tsx`
- Modify: `frontend/src/app/(dashboard)/error.tsx`

### Step 1: Update all loading.tsx files

Replace Skeleton shimmer with blinking cursor loading state. Each loading page should match its page's layout structure but with `_` cursor placeholders instead of content:

```tsx
export default function DashboardLoading() {
  return (
    <div className="animate-fade-in space-y-8">
      <div className="h-10 w-48">
        <span className="animate-cursor-blink font-mono text-muted-foreground">_</span>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="border border-border p-6">
            <span className="text-label text-muted-foreground">Loading</span>
            <div className="mt-2">
              <span className="animate-cursor-blink font-mono text-2xl text-muted-foreground">_</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

Adapt similarly for each page's loading state (matching the general layout shape).

### Step 2: Update not-found.tsx

```tsx
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-6">
      <span className="font-display text-[120px] font-black leading-none text-muted-foreground/20">404</span>
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
```

### Step 3: Update error.tsx

Style the error page with brutalist aesthetics — uppercase mono text, accent-colored error message.

### Step 4: Verify & commit

```bash
cd frontend && npx tsc --noEmit && npm run build
git add frontend/src/app/
git commit -m "feat(frontend): redesign loading states, 404, and error pages — blinking cursor aesthetic"
```

---

## Task 12: Final Verification & Cleanup

### Step 1: Full build verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

### Step 2: Search for leftover generic styles

Grep for patterns that should no longer exist:
- `rounded-full` (except in status dots where intentional)
- `rounded-xl`
- `shadow-md`, `shadow-lg`
- `backdrop-blur`
- References to Inter font
- `bg-emerald-`, `bg-blue-`, `bg-yellow-` etc (should be replaced with CSS variable status colors)

### Step 3: Visual review with dev server

```bash
cd frontend && npm run dev
```

Check each page in the browser to verify the brutalist aesthetic is consistent.

### Step 4: Commit any cleanup

```bash
git add -A frontend/
git commit -m "chore(frontend): clean up leftover generic styles from redesign"
```
