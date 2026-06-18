# AGENTS.md — FinSight AI UI Design System

## Project Stack

This project uses:

```txt
Frontend: React
Backend: FastAPI
Database: MySQL
Styling: CSS / Tailwind CSS if already used
Charts: Recharts
Icons: lucide-react
```

The UI must follow one consistent design system across all sidebar pages:

```txt
Dashboard
Wallet
Transactions
Categories
Upload Statement
Friends
AI Insights / AI Advisor
Settings
```

Do not design each page differently. Every page should feel like part of one premium financial product.

---

# Core UI Direction

The app should look like a premium dark fintech dashboard.

The style should be:

```txt
Minimal
Dark
Soft
Thin
Professional
Quiet
Premium
Finance-focused
```

The UI should not look like a generic SaaS template, crypto dashboard, gaming UI, or marketing landing page.

The design should feel closer to:

```txt
Modern banking dashboard
Premium analytics tool
Dark finance operating system
```

---

# Main Color Palette

Use these colors consistently.

## Background Colors

### App Background

Use a very dark green-black background.

```css
--bg-main: #080D0F;
rgb(8, 13, 15)
```

Use this for the full page background.

Do not use pure black.

Wrong:

```css
#000000
```

Correct:

```css
#080D0F
#0B1012
#0D1315
```

---

### Sidebar Background

Sidebar should be slightly different from the main background but still very dark.

```css
--bg-sidebar: #0B1012;
rgb(11, 16, 18)
```

It should blend into the layout, not look like a separate heavy panel.

---

### Card Background

Cards should use soft dark surfaces.

```css
--card-bg: #111719;
rgb(17, 23, 25)
```

Alternative elevated card:

```css
--card-bg-elevated: #151C1F;
rgb(21, 28, 31)
```

Card background should not be bright, blue, purple, or fully transparent.

---

### Card Hover Background

```css
--card-hover: #182124;
rgb(24, 33, 36)
```

Use only subtle hover changes.

---

# Border System

Borders should be soft and low contrast.

```css
--border-soft: rgba(255, 255, 255, 0.08);
--border-medium: rgba(255, 255, 255, 0.12);
```

Use thin borders only:

```css
border: 1px solid var(--border-soft);
```

Do not use hard borders like:

```css
#ffffff
#555555
#4b5563
```

Cards should feel separated by spacing and soft borders, not thick outlines.

---

# Accent Colors

## Primary Green

Use this as the main brand accent.

```css
--accent-green: #9BE14B;
rgb(155, 225, 75)
```

Use for:

```txt
Active sidebar item
Positive percentages
Savings indicators
Health score ring
Primary CTA
Selected states
```

Do not overuse it. It should appear as an accent, not cover the whole UI.

---

## Deep Green

Use for darker active backgrounds.

```css
--accent-green-bg: rgba(155, 225, 75, 0.12);
```

Active sidebar item example:

```css
background: rgba(155, 225, 75, 0.10);
border-left: 3px solid #9BE14B;
color: #9BE14B;
```

---

## Red / Negative

Use soft red for expenses, negative trends, warnings.

```css
--accent-red: #FF5A52;
rgb(255, 90, 82)
```

Use it only for:

```txt
Expense trend
Overspending
Negative percentage
Budget exceeded
```

---

## Amber / Warning

Use muted amber for medium-risk financial states.

```css
--accent-amber: #E5A93A;
rgb(229, 169, 58)
```

Use for:

```txt
Moderate health score
Budget warning
Review required
```

---

# Text Colors

## Main Text

```css
--text-primary: #F3F5F2;
rgb(243, 245, 242)
```

Use for:

```txt
Page titles
Large numbers
Important labels
```

---

## Secondary Text

```css
--text-secondary: #B8C0BA;
rgb(184, 192, 186)
```

Use for:

```txt
Subtitles
Card labels
Table headers
Small descriptions
```

---

## Muted Text

```css
--text-muted: #7D8781;
rgb(125, 135, 129)
```

Use for:

```txt
Timestamps
Small hints
Less important metadata
```

---

# Typography Rules

Use a clean modern sans-serif.

Preferred fonts:

```css
font-family: Inter, "SF Pro Display", "Segoe UI", system-ui, sans-serif;
```

If using Google Fonts, use:

```txt
Inter
Geist
Manrope
```

## Font Weight Rules

The UI must look thin and premium.

Use:

```txt
300 for large greetings
400 for body text
500 for labels and card titles
600 only for important headings
```

Avoid heavy bold text everywhere.

Do not use:

```txt
font-weight: 700 repeatedly
font-weight: 800
font-weight: 900
```

---

# Number Styling

Financial numbers should be clean, thin, and elegant.

Use:

```css
font-weight: 400;
letter-spacing: -0.03em;
font-variant-numeric: tabular-nums;
```

Large card numbers:

```css
font-size: 24px;
font-weight: 400;
line-height: 1.1;
```

Dashboard hero numbers:

```css
font-size: 30px;
font-weight: 400;
letter-spacing: -0.04em;
```

Do not make numbers thick or overly large.

---

# Layout Rules

## Page Layout

All pages should follow this layout:

```txt
Fixed sidebar on the left
Main content in center
Optional right panel only when useful
```

Main page padding:

```css
padding: 28px 32px;
```

Content gap:

```css
gap: 16px;
```

Do not use huge empty spacing.

Do not create oversized cards.

---

# Sidebar Design

Sidebar width:

```css
width: 220px;
```

Sidebar background:

```css
background: #0B1012;
border-right: 1px solid rgba(255,255,255,0.08);
```

Sidebar items should be:

```css
height: 48px;
border-radius: 10px;
padding: 0 16px;
font-size: 14px;
font-weight: 400;
color: #B8C0BA;
```

Active item:

```css
background: rgba(155, 225, 75, 0.10);
color: #9BE14B;
border-left: 3px solid #9BE14B;
```

Icons should be thin line icons.

Use lucide-react icons with:

```css
stroke-width: 1.6;
```

Do not use filled colorful icons.

---

# Card Design

Cards are the most important component.

Use this base card style everywhere:

```css
.card {
  background: linear-gradient(180deg, #111719 0%, #0E1416 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
}
```

Cards should look premium but not glassy.

Do not use glassmorphism.

Avoid:

```css
backdrop-filter: blur(...)
background: rgba(..., 0.2)
```

---

# Summary Metric Cards

Use for:

```txt
Total Income
Total Expenses
Investments
Total Savings
Savings Rate
Top Category
Top Merchant
Subscriptions
Transactions
```

Each metric card should contain:

```txt
Small icon circle
Label
Large value
Small trend text
Optional mini sparkline
```

Example structure:

```txt
[icon] Total Income
       ₹1,28,500
       ▲ 12.6% vs Jun
```

Icon circle:

```css
width: 40px;
height: 40px;
border-radius: 999px;
border: 1px solid rgba(255,255,255,0.12);
background: rgba(255,255,255,0.03);
```

Card label:

```css
font-size: 13px;
color: #B8C0BA;
font-weight: 400;
```

Value:

```css
font-size: 24px;
font-weight: 400;
color: #F3F5F2;
```

Trend positive:

```css
color: #9BE14B;
```

Trend negative:

```css
color: #FF5A52;
```

---

# Category Colors

Category colors must be soft, muted, and premium.

Do not use bright default chart colors.

Use this palette:

```css
--cat-food: #7F86E8;
rgb(127, 134, 232)

--cat-shopping: #F06A61;
rgb(240, 106, 97)

--cat-transport: #E58BB7;
rgb(229, 139, 183)

--cat-bills: #D68FB0;
rgb(214, 143, 176)

--cat-entertainment: #C8C3C7;
rgb(200, 195, 199)

--cat-health: #78BDA0;
rgb(120, 189, 160)

--cat-travel: #8AA0D6;
rgb(138, 160, 214)

--cat-subscriptions: #A9D85A;
rgb(169, 216, 90)

--cat-education: #D9B45F;
rgb(217, 180, 95)

--cat-investments: #8EE06C;
rgb(142, 224, 108)

--cat-other: #8E9AA3;
rgb(142, 154, 163)
```

Use these for:

```txt
Pie charts
Category badges
Category dots
Category legends
```

Category badges should have tinted backgrounds:

```css
background: rgba(categoryColor, 0.12);
border: 1px solid rgba(categoryColor, 0.22);
color: categoryColor;
```

---

# Charts Design

Do not use default Recharts styling.

Charts should be minimal.

## Chart Rules

```txt
No bright colors
No thick grid lines
No cluttered axis labels
No huge legends
No default tooltips
No large chart titles
```

Grid:

```css
stroke: rgba(255,255,255,0.06);
```

Axis labels:

```css
fill: #7D8781;
font-size: 12px;
```

Line chart income:

```css
stroke: #9BE14B;
stroke-width: 2;
```

Line chart expenses:

```css
stroke: #FF5A52;
stroke-width: 2;
```

Tooltip:

```css
background: #111719;
border: 1px solid rgba(255,255,255,0.10);
border-radius: 10px;
color: #F3F5F2;
```

Pie / donut charts should use soft category colors only.

Do not use neon rainbow colors.

---

# Financial Health Score

Health score should use a circular progress ring.

Good score:

```css
#9BE14B
```

Medium score:

```css
#E5A93A
```

Poor score:

```css
#FF5A52
```

The score number should be large but thin:

```css
font-size: 44px;
font-weight: 300;
letter-spacing: -0.05em;
```

Checklist below score should use small green check icons.

---

# Tables

Tables should be clean and low contrast.

Header:

```css
font-size: 12px;
color: #7D8781;
font-weight: 400;
```

Rows:

```css
height: 56px;
border-bottom: 1px solid rgba(255,255,255,0.06);
```

Main text:

```css
font-size: 14px;
color: #F3F5F2;
```

Secondary text:

```css
font-size: 12px;
color: #7D8781;
```

Do not use white table backgrounds.

Do not use thick row borders.

---

# Buttons

Primary button:

```css
background: #9BE14B;
color: #08100A;
border-radius: 10px;
font-weight: 500;
```

Secondary button:

```css
background: #111719;
border: 1px solid rgba(255,255,255,0.10);
color: #B8C0BA;
```

Danger button:

```css
background: rgba(255, 90, 82, 0.12);
color: #FF5A52;
border: 1px solid rgba(255, 90, 82, 0.25);
```

Buttons should not glow heavily.

Hover should be subtle:

```css
transform: translateY(-1px);
```

---

# Forms and Inputs

Inputs should match cards.

```css
background: #0E1416;
border: 1px solid rgba(255,255,255,0.10);
border-radius: 10px;
color: #F3F5F2;
padding: 12px 14px;
```

Placeholder:

```css
color: #7D8781;
```

Focus:

```css
border-color: rgba(155, 225, 75, 0.55);
box-shadow: 0 0 0 3px rgba(155, 225, 75, 0.08);
```

---

# Page-Specific Rules

## Dashboard Page

Dashboard is the main selling page.

It should include:

```txt
Greeting
Month selector
Filters button
Metric cards
Category spending chart
Income vs Expenses chart
Wallet summary
Recent transactions
AI insight panel
Financial health score card
```

Dashboard must not include detailed budget management.

Budget details belong in Wallet or Budget page.

---

## Wallet Page

Wallet page should contain:

```txt
Investments
Budgets
Savings goals
Subscriptions
Projected savings
Wallet summary
```

Use the same card style as dashboard.

Do not redesign this page separately.

---

## Transactions Page

Transactions page should contain:

```txt
Transaction table
Search
Filters
Category badges
Amount type indicators
Date filter
Merchant filter
Export option
```

Keep the table minimal and readable.

---

## Categories Page

Categories page should contain:

```txt
Category list
Category colors
Spending per category
Merchant rules
Learned category rules
Category correction history
```

Use soft category colors only.

---

## Upload Statement Page

Upload page should feel simple and operational.

It should contain:

```txt
Upload dropzone
Supported file types
Import confidence
Column mapping preview
Parsed transaction preview
Confirm import button
```

Dropzone should be dark and bordered softly.

Do not use huge illustrations.

---

## Friends Page

Friends page should contain:

```txt
Friend list
Friend spending summary
Detected friend transactions
Shared transactions
Friend transaction history
```

Keep the same finance card style.

Do not make it social-media-like.

---

## AI Advisor / AI Insights Page

This page should feel like a financial command center, not a generic chatbot.

It should contain:

```txt
Advisor input box
Suggested prompts
AI response cards
Recommended actions
Savings impact
Subscription suggestions
Chat history
```

Chat bubbles should be minimal.

Do not use WhatsApp-style chat design.

AI response should be shown in cards:

```txt
Summary
Main Problem
Recommendation
Expected Impact
```

---

# Animation Rules

Animations should be subtle.

Allowed:

```txt
Card hover lift
Soft fade in
Smooth chart loading
Button hover
Sidebar active transition
```

Use:

```css
transition: all 180ms ease;
```

Avoid:

```txt
Bouncy animation
Large motion
Flashing effects
Heavy glow animation
```

---

# Responsive Rules

Primary target is laptop view.

Minimum width priority:

```txt
1366px and above
```

Dashboard should look best on laptop/desktop.

Do not optimize for mobile first.

Use responsive grids but keep laptop layout as the main design.

---

# DON'T

Do not use bright gradients.

Do not use glassmorphism.

Do not use overly colorful cards.

Do not use hard borders.

Do not use pure white backgrounds.

Do not use large illustrations.

Do not use marketing-style hero copy.

Do not create excessive chart clutter.

Do not use generic SaaS dashboard spacing.

Do not use default Recharts styling.

Do not make every card a different bright color.

Do not use heavy font weights everywhere.

Do not make the UI look like a template.

Do not add unnecessary components.

Do not place budget management on the main dashboard.

Do not overuse shadows or glow.

Do not use childish colors.

Do not make cards too large with empty space.

Do not use boring gray-on-gray without contrast.

Do not use neon colors.

Do not use thick borders.

Do not use default blue links.

Do not use pure black backgrounds.

Do not use white cards.

Do not make chart legends too large.

Do not create inconsistent spacing between pages.

---

# Final Design Goal

Every page should look like the same premium fintech product.

The user should feel:

```txt
Clean
Focused
Professional
Financially serious
Modern
Premium
```

The final UI should look custom-built, not like a dashboard template.
