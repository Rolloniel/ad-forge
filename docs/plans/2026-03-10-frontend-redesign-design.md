# AdForge Frontend Redesign — "Concrete & Steel"

**Date:** 2026-03-10
**Direction:** Elegant Minimal Brutalist
**Scope:** Full sweep — all pages, sidebar, shell, login

## Aesthetic Summary

Raw, light, architectural. Brutalist structure with Swiss design restraint. Near-white concrete backgrounds, black type, hairline borders, zero border-radius, zero shadows. A single muted terracotta accent used surgically. Monospace UI chrome paired with tight grotesque headings. Feels like a creative director's blueprint tool.

## Design Tokens

### Colors

| Token | Light | Dark |
|---|---|---|
| Background | `#F2F0ED` | `#1A1A1A` |
| Surface | `#FFFFFF` | `#2A2725` |
| Border | `#D4D0CB` | `#3A3735` |
| Hover | `#E8E5E1` | `#332F2C` |
| Text primary | `#1A1A1A` | `#F2F0ED` |
| Text secondary | `#6B6560` | `#9B9590` |
| Accent (terracotta) | `#B04A32` | `#B04A32` |
| Status: completed | `#4A6B52` | `#4A6B52` |
| Status: failed | `#8B3A3A` | `#8B3A3A` |
| Status: running | `#B04A32` | `#B04A32` |
| Status: pending | `#9B9590` | `#9B9590` |

### Typography

| Role | Font | Size | Weight | Style |
|---|---|---|---|---|
| Page title | Darker Grotesque | 32px | 900 | Uppercase, `letter-spacing: 0.05em` |
| Section header | Darker Grotesque | 20px | 700 | — |
| Body/labels | IBM Plex Mono | 13px | 400 | — |
| Small/meta | IBM Plex Mono | 11px | 400 | Secondary color |
| Buttons | IBM Plex Mono | 12px | 500 | Uppercase, `letter-spacing: 0.08em` |
| Large metrics | Darker Grotesque | 36px | 900 | — |

Intentional gap between 13px and 20px — no sizes in between. Creates tension between mono body and grotesque headers.

### Globals

- `border-radius: 0` everywhere
- No box-shadows anywhere
- Depth via borders and spacing only
- Tabular figures for numbers in tables/metrics

## Sidebar & Shell

### Sidebar (~200px)

- Background: `#1A1A1A`, full height
- Logo: "ADFORGE" in Darker Grotesque, 900 weight, `#F2F0ED`, letter-spaced
- Nav items: IBM Plex Mono, 12px, uppercase, `#9B9590` default
- Active: `#F2F0ED` text + 2px solid terracotta left border, no background
- Hover: `#F2F0ED` text, no background
- 12px vertical gap between items
- Text-only navigation — no icons
- Bottom: theme toggle + "v0.1" in 10px secondary gray

### Shell

- No header bar — content starts immediately, page title acts as header
- Content: max-width 1200px, centered, 48px horizontal padding
- Mobile: sidebar → top bar with hamburger → full-screen black overlay drawer with large nav text

### Borders & Dividers

- 1px `#D4D0CB` everywhere
- No rounded corners, no shadows

## Component Styling

### Cards

- White background, 1px hairline border, 0 radius, no shadow, 24px padding
- Titles: 11px mono, uppercase, letter-spaced, secondary color (label, not heading)
- Large values: Darker Grotesque, 36px, weight 900

### Buttons

- **Primary:** `#1A1A1A` bg, `#F2F0ED` text, 0 radius. Hover → `#B04A32` bg
- **Outline:** Transparent bg, 1px `#1A1A1A` border. Hover → `#1A1A1A` fill, text inverts
- **Ghost:** No border/bg, uppercase mono text. Hover → underline
- All: 12px mono, uppercase, wide tracking, `padding: 10px 20px`

### Badges

- Rectangular, 1px border matching status color, transparent bg, status color text
- All caps, 10px mono

### Tables

- Full-width, no outer border
- Header: 11px mono, uppercase, secondary color, bottom border only
- Rows: 13px mono, bottom hairline. No zebra striping.
- Hover: `#E8E5E1` full row

### Form Inputs

- Bottom border only (no full box), full box border on focus
- Focus: 2px `#B04A32` border, no glow
- Labels: 11px mono, uppercase, secondary color, above input

### Dialogs

- Dark semi-transparent overlay (`rgba(26,26,26,0.6)`), no blur
- Modal: white, 0 radius, hairline border, 32px padding

## Page Designs

### Login

- Centered on `#F2F0ED` background
- "ADFORGE" Darker Grotesque 48px weight 900
- "CREATIVE INFRASTRUCTURE" 11px mono subtitle
- Single bottom-border input + black button. No card wrapper.

### Dashboard

- "DASHBOARD" page title, Darker Grotesque
- 4 KPI cards: 11px uppercase label + 36px value, no icons
- "RECENT RUNS" table directly on page background, no card wrapper
- System status: 3 inline text items with small colored dots
- Quick launch: row of outline buttons

### Pipelines

- Full-page state change per phase (not wizard)
- Selection: rectangular cards, selected = `#1A1A1A` fill + white text
- Config: stacked form, rectangular toggle chips for product/audience
- Running: vertical timeline, terracotta left border on active step, strike-through on completed
- Recent jobs sidebar: simple list with mono text + status badges

### Brands

- Card grid: name in Darker Grotesque 20px, voice in 13px mono (2-line clamp), counts as "3 PRODUCTS · 2 AUDIENCES" in 11px secondary mono
- Edit modal: full-width sections separated by hairline borders

### Gallery

- Filter bar: inline bottom-border selects + "CLEAR" ghost button
- Output grid: preview fills card top, metadata below in mono
- Preview modal: large preview left, key-value metadata right
- Batch: checkbox on hover, fixed bottom bar with count

### Performance

- 6 KPIs: no card borders, separated by thin vertical hairlines
- Charts: terracotta primary, `#1A1A1A` secondary, `#D4D0CB` gridlines. No gradients. Transparent bg.
- Insights: plain text with terracotta left border (blockquote style)

### Deployment

- Tabs: uppercase mono text + 2px terracotta bottom border indicator
- Campaign tree: indented text with CSS border-left connectors, all visible (no accordion)
- JSON viewer: `#F7F5F2` bg, hairline border. Highlighting: black keys, gray strings, terracotta numbers/booleans

## Motion

Restrained and mechanical — no playful/bouncy animations.

- **Page load:** Content `opacity 0→1` over 200ms, no transform
- **Staggered reveals:** KPI cards and grid items stagger with 50ms delay, opacity only
- **Button hover:** Background swap, 100ms
- **Table row hover:** Background fill, 80ms
- **Nav hover:** Color snap, no transition
- **Card hover:** `translate(-2px, -2px)` + `box-shadow: 4px 4px 0 #1A1A1A`, 120ms. The one playful brutalist touch.
- **Pipeline active step:** Terracotta left border pulses opacity `1→0.4→1` over 2s (CSS)
- **Step completion:** `text-decoration: line-through`, 300ms transition
- **Loading:** Blinking underscore cursor `_` in mono text (CSS animation), no skeleton shimmer
- **Toasts:** Slide from bottom-right, black bg, white mono text, no icon. 4s auto-dismiss with shrinking terracotta progress bar
