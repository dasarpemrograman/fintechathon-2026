# Green visual system and English interface

Implemented on 19 October 2026, following the [Grand Design Visual](grand-design-visual.md), [visual board](grand-design-visual.png) and [HTML design specimen](grand-design-visual.html). The design artifacts were created before the application refresh.

## Delivered experience

- Forest-green application navigation, neutral working surfaces, consistent spacing/type, local vector icons and a shared responsive component treatment.
- A focused sign-in screen with a separate, explicitly synthetic offline demo entry.
- An API-backed portfolio with product/route search, Deal/Exploration filters, loaded-view counts, explicit loading/empty states and retained pagination.
- Numbered workspace navigation from overview and evidence through economics, scenarios, drafts, readiness, settlement and history. Status dimensions remain server-derived; section position does not claim business completion.
- A contextual overview guide, compact status summary, readable forms/tables, original-source disclosure and a persistent synthetic-demo banner.
- English navigation, labels, explanations, validation guidance, metadata and date formatting. English is also the default draft, automated recommendation and finance-pack language. Indonesian commercial drafts remain an explicit choice; stored originals and historic artifacts are retained unchanged.
- Keyboard skip navigation, visible focus, explicit labels, restrained status colors, reduced-motion handling and responsive layouts without page-level horizontal overflow in the tested journeys.

## Executed checks

The production Next.js image build and TypeScript checks pass. The final full browser run passes **24/24 journeys** against the actual PostgreSQL/API/worker/web stack. These include normal/demo authentication, organization isolation, source research, real job completion, funding scenarios, English draft download, goods-review permissions, receipts/reversal, reconciliation/closure, history/archival and Calendar callback/projection/conflict/revocation.

The added visual checks cover **320, 390, 768 and 1440px** viewport widths, default English draft selection, navigation state, search/filter behavior, keyboard skip focus, absence of JavaScript page errors and absence of page-level horizontal overflow. The rendered primary button text/background contrast meets 4.5:1. Desktop/mobile screenshots were also inspected. These targeted checks do not constitute independent certification of every WCAG criterion.

The focused backend artifact, financing-preparation, workflow and bounded-model suites pass **30 tests**, including generated English finance-pack headings and retained explicit Indonesian template support. One existing Starlette/httpx deprecation warning remains. The final runtime doctor reports web, API, PostgreSQL, matching worker and seeded identities ready.

Browser assertions were updated to the new English accessible names. The local Compose Calendar test helper now invokes Docker Compose directly, matching the documented native Windows workflow. The public onboarding and walkthrough labels have been updated to the rendered interface.

No live-provider acceptance is inferred from this offline visual refresh. Original evidence, currencies, local-date/timezone semantics, role boundaries and immutable approval/history checks continue to use the existing domain and API services.
