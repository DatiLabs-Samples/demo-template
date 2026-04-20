# Frontend Guidelines — Vite + React + TypeScript + Cloudscape

Stack: Vite.js, React 18+, TypeScript, AWS Cloudscape Design System
Styling: Cloudscape built-in (NO Tailwind)

## Official References

- Components: https://cloudscape.design/components/
- Patterns: https://cloudscape.design/patterns/
- Get started: https://cloudscape.design/get-started/guides/introduction/
- Layout guide: https://cloudscape.design/get-started/guides/building-a-layout/
- Demos: https://cloudscape.design/demos/

## Setup

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install @cloudscape-design/components @cloudscape-design/global-styles
npm install @cloudscape-design/collection-hooks @cloudscape-design/design-tokens
```

Entry point must import `@cloudscape-design/global-styles/index.css`.

Always use individual imports for tree-shaking: `import Button from "@cloudscape-design/components/button"` — never barrel imports.

## App Shell

Every Cloudscape app uses `TopNavigation` + `AppLayout`. Choose ONE layout type per product:
- **AppLayout** — browsing/expressive use cases (docs, marketing)
- **AppLayoutToolbar** — productive/data-dense use cases (always with breadcrumbs)

Structure: `TopNavigation` at top → `AppLayout` wrapping `SideNavigation` (left), `Flashbar` (notifications), `BreadcrumbGroup`, and page content.

See: https://cloudscape.design/components/app-layout/

## Page Layout

Standard page uses `ContentLayout` + `Header` + `Container` + `SpaceBetween`.

Rules:
- Use `SpaceBetween` for spacing — never manual margins
- Use `Box` for styled text elements
- Use design tokens for colors — never raw hex values
- Key-value pairs: `ColumnLayout` with `variant="text-grid"` + `Box variant="awsui-key-label"`
- One `h1` per page via `Header variant="h1"`

See: https://cloudscape.design/components/content-layout/, https://cloudscape.design/components/container/

## Forms

Rules:
- Always wrap inputs in `FormField` (handles label association and error display)
- Use `SpaceBetween size="l"` between fields
- Use `constraintText` for format hints (e.g., "Must be 1 to 100 characters")
- Never disable the submit button — it serves as fallback validation trigger
- All Cloudscape form components use `event.detail` for values
- Validate on-blur for populated fields, on-submit for all required fields
- On error: show all errors, scroll to topmost, focus it
- Never validate on first page visit

See: https://cloudscape.design/components/form/, https://cloudscape.design/patterns/general/form-validation/

## Tables

Use `useCollection` from `@cloudscape-design/collection-hooks` for filtering, sorting, and pagination state.

Rules:
- Always provide `empty` and `noMatch` states in `useCollection` config
- Use `loading` and `loadingText` props during data fetch
- Use hyphen (`-`) for empty cell values — never blank, never "N/A"
- **Table vs Cards:** Use Table when users compare attributes across rows. Use Cards when items are self-contained and browsed individually. Both use `useCollection()`.

See: https://cloudscape.design/components/table/, https://cloudscape.design/patterns/general/cards-and-tables/

## Cloudscape Patterns & Best Practices

### Loading

Time-based feedback: <1s no feedback, 1–10s `Spinner`, >10s `ProgressBar`. Add refresh button in `Header` actions with a "Last updated" timestamp. Use ARIA live regions for timestamp announcements.

See: https://cloudscape.design/patterns/general/loading/

### Error Handling

Three scopes:

| Scope | Component | When |
|-------|-----------|------|
| Field-level | `FormField errorText` | Inline validation |
| Page/section | `Alert type="error"` | Server errors, failed sections |
| Global status | `Flashbar type="error"` | Operation failures |

Error message rules: use `"[Label] is required."` for required fields, `"Enter a valid [label]."` for format errors. Never show raw machine errors. Never say "Fix all errors" — be specific.

See: https://cloudscape.design/patterns/general/error-handling/

### Empty States

Two distinct states — always provide an action button:
- **Empty** (no resources exist): heading + description + create button
- **No matches** (filter returned nothing): heading + clear filter button

Use hyphen (`-`) for empty values in cells and key-value pairs.

See: https://cloudscape.design/patterns/general/empty-state/

### Flashbar

Exclusively for status notifications at page top (success, error, info, warning, in-progress). Use `Alert` for contextual in-page messages. Use `Flashbar` for operation outcomes.

See: https://cloudscape.design/patterns/general/flashbar/

### Density

Default to comfortable mode. Store preference in localStorage. Comfortable is default because compact can hinder readability for users with vision impairment.

See: https://cloudscape.design/patterns/general/density/

### Writing

Sentence case everywhere. No exclamation points, no "please"/"thank you". Active voice, present tense. Use "choose"/"select" not "click". Headings: bold, no end punctuation. Descriptions: end punctuation, never repeat heading text.

## API Communication

Create a thin fetch wrapper (`services/api.ts`) with typed `get`/`post`/`put`/`delete` methods that throw a typed `ApiError` on non-OK responses.

Create a `useApi<T>(fetcher)` hook that returns `{ data, loading, error, refetch }` — handles loading state, error capture, and re-fetch.

Frontend uses relative URLs (`/api/...`, `/ws/...`) — Vite proxy routes to backend.

## Theming

Use `applyMode(Mode.Dark | Mode.Light)` and `applyDensity(Density.Compact | Density.Comfortable)` from `@cloudscape-design/global-styles`. Persist preference in localStorage.

See: https://cloudscape.design/foundation/visual-foundation/

## Responsive Design

Cloudscape `Grid` uses `colspan` with breakpoints: `default`, `xs` (480px), `s` (688px), `m` (1080px), `l` (1280px), `xl` (1440px). `AppLayout` handles responsive navigation collapse automatically.

See: https://cloudscape.design/components/grid/

## Accessibility

Cloudscape is WCAG 2.1 AA compliant by default. Maintain by:
- Always `ariaLabel` on icon-only buttons
- Always wrap form controls in `FormField`
- Use `Header` for heading hierarchy — one `h1` per page
- Use `Link` for navigation, `Button` for actions
- Never `div` with `onClick` — use `Button` or `Link`
- Use `LiveRegion` for dynamic content announcements
- Never use color alone to convey information

## Vite Proxy

In `vite.config.ts`, proxy `/api`, `/ws`, `/health` to `http://localhost:8000`. Frontend uses relative URLs.

## Common Patterns

For implementation examples of these patterns, see the official demos:
- **Dashboard:** https://cloudscape.design/demos/dashboard/
- **Table with actions:** https://cloudscape.design/demos/table/
- **Create form:** https://cloudscape.design/demos/create-form/
- **Detail page with tabs:** https://cloudscape.design/demos/detail-tabs/
- **Delete confirmation modal:** use `Modal` with footer containing Cancel (link variant) + Confirm (primary variant)
- **Split panel:** use `AppLayout splitPanel` prop with `SplitPanel` component
- **Cards view:** use `Cards` component with same `useCollection` as Table
