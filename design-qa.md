**Comparison Target**

- Source visual truth: Browser annotation screenshot supplied in the current conversation for `/dashboard/category-analytics`.
- Implementation screenshot: In-app Browser capture of `http://localhost:5173/dashboard/category-analytics` from 2026-07-03.
- Viewport: 1186 × 698 desktop.
- State: February 2026 category analytics, loaded state, no tooltip pinned.

**Full-view Comparison Evidence**

- The former shared section surface is now transparent, borderless, shadowless, and unpadded.
- Seven category charts render as seven independent two-column cards with a consistent 24px grid gap.
- Card styling resolves to the Dashboard design tokens: 1px border, 14px radius, Dashboard gradient background, 24px padding, and no shadow.
- All seven chart frames remain rendered and interactive; the redundant merchant detail lists are absent.

**Focused Region Comparison Evidence**

- No extra focused crop was required because the card boundaries, spacing, headers, and chart frames are clearly readable in the full viewport capture.

**Findings**

- No actionable P0, P1, or P2 visual mismatches remain within the requested scope.
- Typography, colors, copy, and chart rendering remain unchanged from the existing application.
- No image assets are involved in this scoped change.

**Patches Made**

- Removed merchant detail-list markup beneath every bar chart.
- Removed all obsolete merchant-list CSS.
- Neutralized the category grid container's inherited card surface.
- Matched each chart card to the Dashboard border, radius, background, padding, shadow, and spacing tokens.

**Implementation Checklist**

- [x] Outer visual wrapper removed.
- [x] Merchant lists removed.
- [x] Dashboard card styling applied.
- [x] Chart data, tooltip, animation setting, and interactions preserved.
- [x] ESLint passed.

**Follow-up Polish**

- None required for this scope.

final result: passed
