# Live acceptance — 18 October 2026

Tasks **11.5 and 12.3 are complete** for the declared local acceptance scopes. All 74 implementation tasks are checked. This records local test acceptance, not production readiness or universal regulatory coverage.

## Calendar lifecycle

The real OAuth callback completed for the configured Google account and its dedicated acceptance calendar. A Google Calendar API read verified the calendar name, owner access, and enabled API. The registered callback was `http://127.0.0.1:3000/oauth/calendar/callback`.

The user approved the exact event title, dates, changes, and cleanup. Testing used a temporary normal-mode acceptance API with a test-run reference, while the normal API's live-write flag remained false. The regular worker was stopped while the acceptance runner exercised production job/outbox delivery, then restarted.

| Check | Retained result |
|---|---|
| Real insert | Google accepted one private, transparent, reminder-free event for 19 October 2026, 10:00–10:15 Asia/Jakarta. No guests or conference link. |
| Ambiguous response | The harness discarded the successful real insert response. The outbox recorded a retryable failure. |
| Retry | A second insert with the same ID received a conflict; reading that owned event resolved it successfully. Exactly one matching active event existed. |
| Approved update | The same event moved to 10:30–10:45. |
| External edit and ETag | A test-only external description changed the provider ETag. A stale attempt to move the event to 11:00 was refused; the external description and 10:30 time remained intact. |
| Delete | After explicit conflict resolution and a new deletion approval, the owned event was deleted and its cancelled/absent state verified. |
| Revoke | Local encrypted credentials were removed, the connection became revoked, and subsequent sync returned HTTP 409. Google's linked-app search showed no Fincathon grant. The built-in timeline remained readable and unchanged by revocation. |

The first run exposed a real retry defect: Google canonicalizes an instant's UTC offset, so direct JSON equality incorrectly reported an external edit. `event_matches` now compares aware instants while preserving named timezone and all-day semantics and the managed privacy fields. A regression rejects actual time changes and re-enabled default reminders. Installation-specific provider identifiers are retained only in private receipts.

Google briefly continued to accept an already-issued access token after the revoke request. An extra harness assertion expecting immediate token invalidation therefore failed after event cleanup. Completion was verified separately through Google's grant list, removed local credentials, refused future sync, and preserved timeline. That historical harness result remains in the receipt; it is not represented as an HTTP 401 that never occurred.

The test event is removed, the grant is revoked, and normal Calendar writes remain disabled. A future deliberate connection needs fresh consent; acceptance does not silently reconnect the account.

## Declared goods and routes

These are operator-selected illustrative test goods, not claims about a customer's inventory. National tariff suffixes, duty treatment, and shipment-specific controls remain separate from the international six-digit heading.

| Route | Precise test goods | HS6 candidate and basis |
|---|---|---|
| Indonesia → Singapore | Unroasted, non-decaffeinated, unmixed Coffea arabica green beans, for beverage manufacture, bulk 60 kg bags; no organic/civet-coffee claim. | **090111**, [official nomenclature, chapter 9](https://hts.usitc.gov/reststop/file?filename=Chapter+9&release=2026HTSRev1). |
| China → Singapore | Bare unpopulated rigid two-layer FR-4 printed circuit boards, 100 × 100 mm, 1.6 mm thick, 1 oz copper, lead-free HASL, no mounted or embedded components; 1,000-piece illustrative lot. | **853400**, [official nomenclature, chapter 85](https://hts.usitc.gov/reststop/file?filename=Chapter+85&release=2026HTSRev1). This excludes populated assemblies. |
| Kenya → Germany | Plain dried mango slices for human consumption, no added sugar or sulphites, not candied/otherwise prepared; non-organic test assumption, food-grade liners in 10 kg cartons. | **080450**, [official nomenclature, chapter 8](https://hts.usitc.gov/reststop/file?filename=Chapter+8&release=2026HTSRev1). Prepared/candied fruit needs separate classification. |

Only the international heading descriptions are used from the US schedule; US rates and statistical suffixes are excluded from every test lane.

## Real source evidence

The application performed **9 Brave searches**, retrieved and parsed **18 HTTPS sources**, obtained live FX for **IDR→SGD, CNY→SGD, and KES→EUR**, and passed its configured Gemini adapter with `gemini-flash-lite-latest`. Source bodies remain private under `.local/acceptance-source-receipts/`; reports retain their URLs, retrieval times, hashes, normalized text locators, applicability assessments, and explicit exclusions.

Discovery also used Exa to review 53 search results across 15 targeted searches. Exa's discovery records were supplemental; acceptance receipts came from the application's Brave and bounded public retrieval adapters.

| Source category | Retrieved sources and scope assessment |
|---|---|
| Indonesian export | [Customs export procedure](https://www.beacukai.go.id/tata-laksana-ekspor) and [government coffee-to-Singapore guide](https://lamansitu.kemendag.go.id/content/persyaratan-mutu-kopi-singapura). Commercial declaration and food guidance retained; civet-coffee-only rules excluded. |
| Singapore food import | [SFA commercial food requirements](https://www.sfa.gov.sg/food-import-export/commercial-imports/import-requirements-for-food-food-products). Product-category and importer predicates remain explicit; meat/fish/egg conditions are excluded from coffee. |
| China export | [China Customs declaration guide](https://online.customs.gov.cn/static/pages/guides/000629002001/000629002001.html). Outbound declaration and accompanying commercial documents retained; no inward-China rule substitution or blanket export-control clearance. |
| Singapore goods import | [Customs import operations](https://www.customs.gov.sg/doing-business/import-operations/import-operations-overview/). Classification/permit workflow retained; final CA controls depend on the actual board specification/end use. |
| Kenya export | [Government export procedure guide](https://infotradekenya.go.ke/menu/855). Commercial registration/customs process retained; fresh-produce certificates are not automatically imposed on dried slices. |
| EU/Germany import | [European Commission plant-product trade rules](https://food.ec.europa.eu/plants/plant-health-and-biosecurity/trade-plants-plant-products-non-eu-countries_en) and [CBI dried-mango market entry](https://www.cbi.eu/market-information/processed-fruit-vegetables-edible-nuts/dried-mango/market-entry). Listing-specific plant-health predicates and product-specific food-safety/market guidance retained; no unsupported claim that dried mango must meet a fresh-fruit certificate rule. |
| Finance | [Indonesia Eximbank PMKE](https://www.indonesiaeximbank.go.id/product-services/pembiayaan-modal-kerja-ekspor-pmke), [ICBC Packing Loan](https://www.icbc.com.cn/en/column/1438058479532523652.html), and [KCB Trade Finance](https://ke.kcbgroup.com/products/trade-finance). Borrower eligibility, price, and tenor remain unknown unless published and applicable. |
| Coffee market | [ICO October 2026 indicator](https://ico.org/documents/I-CIP.pdf): the latest populated row captured was 15 October, I-CIP **260.37 US cents/lb**. It is an indicator, not an Indonesian grade/lot/Incoterm quote; the blank 16 October row was not filled in. |
| PCB market | [Manufacturer's public offer](https://jlcpcb.com/) showed a starting prototype tier of **USD 2 for 5 pieces**. It was rejected as an executable comparator for the 1,000-board specification; a design-specific quotation is required. |
| Dried-mango market | [CBI](https://www.cbi.eu/market-information/processed-fruit-vegetables-edible-nuts/dried-mango/market-entry) describes an indicative natural dried-mango FOB range of **EUR 8–12/kg**. This is not a Kenyan supplier offer or a delivered-Germany price; retail end-market figures were excluded. |
| Logistics | [Singapore carrier routes](https://www.maersk.com/local-information/asia-pacific/singapore/routes) and [Kenya carrier routes](https://www.maersk.com/local-information/africa/kenya/routes). Service/port references retained; no sailing, transshipment, transit time, capacity, or freight charge was invented. |

Finance comparisons preserve stage and instrument restrictions: ICBC's packing loan requires an acceptable LC/credit line and its published maximum is not an approval; KCB's post-shipment invoice discounting cannot fund a pre-shipment production gap. PMKE's published currency scope is IDR or available foreign currencies; an unpublished rate stays quote-required.

Initial DNS and site-access failures are retained. Serial retries, preferring a validated public IPv4 address on dual-stack WSL, an accessible official Singapore Customs source, and recognizing a bounded PDF with a valid signature when served as generic binary resolved retrieval. All DNS answers still undergo public-address checks; redirects, TLS hostname verification, size, time, and content-type controls remain enforced. Other binary content stays blocked. Each probe/retry is bounded separately and reuses successful receipt evidence explicitly.

## Reproduce and inspect

Use the normal environment and the manifest at `config/live-acceptance-scopes-v1.json`:

```sh
python scripts/probe_live_providers.py
python scripts/probe_acceptance_sources.py --workers 1
python scripts/review_acceptance_sources.py
```

If retrying, preserve the prior source report under another private filename and pass `--retry-from <file>`; successful prior receipts keep their original retrieval times. The probe's `coverage_acceptance` remains false because retrieval alone is not the review verdict. The separate review artifact and this report provide the limited-scope acceptance decision.

Sanitized retained artifacts: `calendar-live-acceptance.json`, `calendar-grant-revoked.png`, `acceptance-source-probes.json`, `acceptance-source-review.json`, and `live-provider-probes.json` in the local output directory. No credentials, tokens, original private uploads, or source bodies are published in these artifacts.
