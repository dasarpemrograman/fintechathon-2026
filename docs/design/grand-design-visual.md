# ALLExport — Grand Design Visual

Direction: **Quiet confidence. Clear decisions.**

This design is defined before implementation. It refreshes the existing Next.js application and makes English its default interface language. Original evidence, stored user content, currencies, contractual local dates, role boundaries and derived business gates retain their meaning.

## Visual system

Forest green `#123C2F` anchors navigation and the brand. Action green `#176C4A` identifies primary actions. Mint `#E8F3EC` supports selected states and quiet panels. Canvas `#F5F7F4`, white surfaces, ink `#182D24`, muted ink `#57685F` and structural borders `#DCE5DE` provide a restrained working environment. Amber `#8A5A13` signals a review or unknown; red `#A23535` signals an error or blocker. Text and icons always accompany status color.

Use the local system sans-serif stack, tabular financial numerals, 14–15px body text, 12–13px supporting text, 20–24px section titles and a 32–40px page title. Follow a 4px spacing base with 8/12/16/24/32/48px intervals. Prefer flat white surfaces, a 12–16px radius, subtle borders, generous spacing and limited motion. No external fonts or visual assets are required for the offline demo.

## Information architecture and flow

1. **Sign in:** a calm introductory panel explains the export decision workflow; normal sign-in and a clearly marked synthetic demo remain distinct.
2. **Workspaces:** product/lane cards, simple search and mode filters lead to an existing workspace or a single primary “New workspace” action. Counts describe the loaded view, never the entire organization without server evidence.
3. **Overview:** product, country, profile and actual current state come first. Primary analysis/setup actions are visible; secondary configuration appears in grouped sections.
4. **Evidence → Economics → Scenarios:** collect and review inputs, inspect known/unknown costs and cash, then compare alternatives. Navigation position is not a readiness or completion claim.
5. **Drafts → Readiness → Settlement:** review exact drafts and agreement requirements before inspecting operational gates and recording external activity or verified settlement.
6. **History:** compare immutable revisions and audit evidence; archive/reactivate only after a deliberate confirmation.
7. **Usage and team:** retain actual plan and membership interfaces, separated from deal decision content by clear section headings and navigation anchors.

Desktop uses a compact forest sidebar and a light content area. Workspace sections use a consistent numbered horizontal navigation rail. Tablet reduces the sidebar footprint; small screens place navigation above the content and keep section navigation horizontally scrollable. Tables scroll inside their own region; forms collapse to one column.

## Components and behavior

- One prominent action per section; secondary actions use neutral outlines and tertiary actions use plain text.
- All controls have visible labels, distinct hover/focus/disabled states and a minimum 44px working height where practical. Keyboard focus uses a high-contrast ring. A skip link reaches the main content.
- Search and filters operate on the loaded workspace view and expose a helpful no-match state and pagination action.
- Headings follow a consistent hierarchy. Native details elements progressively disclose dense reviews, source records and configuration without hiding primary results.
- Loading, queued, running, partial, stale, failed, cancelled and completed states remain explicit. Accepted work is never labeled completed until the worker finishes.
- Unknown values remain “Not yet known”; preserved source language is identified as original evidence. English UI strings never rewrite evidence or turn a synthetic fixture into a live result.
- English becomes the document language, browser metadata, navigation, form guidance, formatting locale and default commercial draft language. Original-source language and alternative draft-language choices remain explicit.
- Respect reduced-motion preferences and keep controls usable at 320–1440px. Avoid motion-dependent understanding.

## Validation gates

Build and TypeScript must pass. Exercise normal/demo entry, workspace creation/editing, analysis jobs, source review, scenario/draft paths, history/archival and Calendar callback states against actual services. Check desktop and 390px layouts, keyboard focus, labels, screenshots, overflow, missing UI translations and runtime errors. Preserve the existing server role and tenant checks.

## References

The interaction approach follows [Nielsen Norman Group usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/): visible state, consistent language, recognition and progressive disclosure. Accessibility targets use [WCAG 2.2](https://www.w3.org/TR/wcag/), including [text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), visible focus and usable control targets. These are implementation targets; full independent WCAG certification is not claimed.
