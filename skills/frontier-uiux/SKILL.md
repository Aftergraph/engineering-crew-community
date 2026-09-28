---
name: frontier-uiux
description: Build or redesign production UI/UX when the request involves a website, app surface, dashboard, landing page, design system, responsive frontend, interaction flow, accessibility, or visual QA. Use the Experience Engineering Plane instead of treating UI as unverified styling.
---
# Frontier UI/UX Builder

Start from the user outcome and product flow, not from decoration. Preserve existing brand and product constraints when present; do not invent a parallel design language without reason.

Model the experience as screens, flows, semantic components, explicit interaction states, data states, design tokens and responsive rules. Keep canonical design decisions in portable tokens and typed contracts rather than scattering magic values through generated code.

For interactive controls, cover default, hover, focus-visible, disabled and component-specific states. Prefer native HTML semantics; use ARIA patterns only where native semantics are insufficient. Require accessible names, visible keyboard focus, non-color-only status, image alternatives and usable target sizes. Treat WCAG 2.2 AA as a baseline, not a visual style.

Responsive behavior should be component-aware. Prefer container-query rules for reusable components and validate at a viewport matrix that includes narrow mobile, tablet, desktop and wide desktop. Define loading, empty, error and ready states where data is asynchronous.

Compile from one ExperienceSpec and design-token source. Generate deterministic artifacts with exact digests. For consequential visual claims, require browser/screenshot receipts bound to the exact artifact digest. Visual QA should cover viewport, theme and reduced-motion cases and fail on unexpected diff, overflow, clipping or excessive layout shift.

Do not equate a successful build with a good experience. Verify flow reachability, semantics, accessibility, responsive behavior and visual evidence independently. Builder and visual verifier should remain separate roles when promotion depends on the result.
