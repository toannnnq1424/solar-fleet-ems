# Global UI contract

User requirement, 19 September 2026: every route shares one visual system and the same sidebar. The latest vendor-account mockup (original #21) is the layout reference for that page. This supersedes earlier freedom concerning its layout.

## Ownership

- `static/app.css` is the single stylesheet for the application and exported HTML reports. No route-specific CSS files, CSS injected by routes, or separate sidebar implementations.
- `:root` owns colors, typography, spacing, radii, shadows, sidebar width and semantic states. New components consume these tokens instead of defining competing palettes.
- `workspace.js` renders the shared shell, navigation, topbar, page heading, dialogs, notifications and scope selector once for every route. Route modules provide content only.
- Shared primitives include button, field, table, badge, card, notice, tabs, dialog, empty/loading/error states. Shared compositions include list + detail panel, two-column content and three-card summary rows. A route may compose these; it must not restyle their meaning.
- VI/EN share structure and spacing. Text wraps naturally; controls do not rely on fixed Vietnamese label widths.
- Source-of-truth navigation keeps duplicated mockup functions in one place. Shortcuts route to the same workflow and authorization, rather than duplicating screens and command execution.

## Consistency and responsiveness

Navy sidebar, white topbar, pale workspace background, blue primary actions, readable tables and clear labels. Success, warning, error and unknown states always include text. Global focus states, keyboard navigation, sufficient control size, responsive stacking and overflow rules apply to all pages. Sidebar behavior is the same on narrow screens.

Do not reproduce example account emails, plant counts, successful diagnostics, token expiry, certificates or savings as production data. Empty and unavailable states keep the reference layout while telling the truth about configured data and available features.

Printed reports reuse `app.css` with `.report-document` content and the global `@media print` rules. Print is an output mode of the shared design system, not a separately branded route.

## Shared energy flow

Site overview and device monitoring both use [energy-flow.js](../src/solar_fleet/static/energy-flow.js). SVG geometry is code; motion/colors/layout remain in global app.css. Flow direction requires fresh accepted measurements; stale/unknown values stop motion. Table view, pause/fullscreen, reduced-motion preference and narrow layouts share the same component. Source-to-load allocation and electrical topology are not inferred from total power readings.

## Change process

Implement reusable styles in `app.css`; reuse an existing primitive before introducing another. New pages must not add `<style>`, stylesheet links or `element.style` declarations. Geometry of plots may use SVG attributes; styling still belongs to the global system. Final QA checks multiple routes and viewport widths in one consolidated pass.
