# ALLExport

### Make the next export decision with the evidence in view.

ALLExport is a workspace for producers and resellers planning an export deal. It brings source documents, commercial terms, costs, cash flow, financing options, drafts, and execution records into one traceable decision flow.

> **The problem:** Export decisions often live across quotations, spreadsheets, messages, and disconnected checklists. A promising margin can hide a cash gap; a paid invoice can hide unfinished delivery or settlement work.
>
> **Our approach:** Show the evidence behind each number, keep unknowns visible, and make the next decision clear without treating a draft or an estimate as an approved action.

## What you can explore

| Step | In ALLExport |
| --- | --- |
| **Start** | Explore a product and route, or create a producer or reseller deal with multiple goods and shipments. |
| **Understand** | Review uploaded evidence, compare source facts, and trace costs, contribution, FX, and dated cash flow back to their inputs. |
| **Decide** | Stress buyer payments, compare negotiation and financing scenarios, and prepare commercial drafts for review. |
| **Follow through** | Track requirements, shipment milestones, verified receipts, actual costs, reconciliation, and closure blockers. |

Changes to reviewed inputs create new revisions. Past evidence and decisions remain available in **History**, so a team can see what changed and why.

## Try the offline demo

The demo starts with synthetic data and needs **Docker with a working daemon and Docker Compose**. You do not need host Python, Node, API keys, or a personal account. The first launch builds the images and prepares local data.

**Windows PowerShell**

```powershell
.\dev.ps1 up
```

**Linux shell**

```sh
./dev up
```

Open **http://127.0.0.1:3000/** and choose **Enter demo**. The demo runs on an isolated Docker network without outbound access; its documents, sources, and financial values are synthetic.

### Suggested judge walkthrough

1. Enter as the **ID owner** and open the base **green-coffee Deal**. In **Economics & cash**, inspect the margin and cash timeline. Use **Overview → Recalculate analysis** to see a real API job completed by the worker.
2. Open **Synthetic coffee · blocked goods** and go to **Readiness & timeline**. The goods-conformity blocker remains visible even when other parts of the deal look ready.
3. Open **Synthetic coffee · closed** to inspect the recorded evidence, actuals, reconciliation, and closure. Compare revisions in **History** to see how the decision evolved.

For a longer tour, follow the [demo walkthrough](docs/demo-walkthrough.md). Stop the stack with `.\dev.ps1 stop` on Windows or `./dev stop` on Linux. Use `doctor` in place of `stop` to diagnose startup issues; the [developer onboarding guide](docs/developer-onboarding.md) covers prerequisites and recovery.

## How it works

The browser is built with **Next.js**. A **Python API** validates commands and serves the workspace; a separate **worker** processes durable jobs. **PostgreSQL** stores business records and revisions, while private content-addressed storage keeps original documents. The [OpenAPI contract](api/openapi.yaml) defines the wire format and generates TypeScript types.

The demo and normal account mode use the same application services. The demo supplies seeded fixtures and offline provider responses; normal mode can be configured for live integrations. See [local runtime](docs/local-runtime.md) for account setup, environment variables, and optional providers.

## Scope and evidence

ALLExport helps people **prepare and review** an export deal. It does not send trade messages, book freight, execute payments, file customs declarations, or submit financing applications. Drafts remain drafts; missing or unverified facts stay explicit. Optional Google Calendar projection is disabled by default in normal mode.

The [verification report](docs/verification.md) records the local implementation checks. [Live acceptance results](docs/live-acceptance-results.md) cover three declared goods and routes and a dedicated Calendar test lifecycle; they are limited-scope evidence, not a claim of production readiness or universal regulatory coverage. The [calculation notes](docs/calculations.md) explain the financial rules.

## For contributors

Start with [developer onboarding](docs/developer-onboarding.md) and the [API contract decisions](docs/contract-decisions.md). Change the canonical OpenAPI YAML before changing wire behavior, then regenerate and check the derived types. The runtime guide documents the full local check sequence and its prerequisites.
