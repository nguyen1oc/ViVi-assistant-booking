# Post-booking knowledge

## Current data provenance

`post_booking_trusted_knowledge.json` is the active schema 2.0 dataset. It contains provenance-aware candidates from official VinFast pages, government guidance, and explicit internal runtime boundaries.

Every current entry is still marked `pending_internal_review`. The service exposes that warning and supports these candidates in development, but a production deployment should construct `KnowledgeService(allow_pending_review=False)` and approve records before serving them.

## Relationship to the component plan

Component 5 in the component plan defines five logical knowledge groups:

1. Vehicle knowledge
2. Test-drive guidance
3. Ownership knowledge
4. Showroom and booking knowledge
5. Curated FAQ and official policies

The schema now supports all five logical groups, provenance, market/model/trim/model-year scope, review status, review dates, and live-data boundaries. Coverage can still grow independently of the schema.

Booking state and availability should continue to come from the booking database and booking services, not from this static JSON. Static knowledge may describe general booking or showroom guidance, but must not duplicate live appointment state.

## Adding knowledge

Add one focused entry under the top-level `entries` array per independently retrievable fact or guidance item. Keep the file valid UTF-8 JSON and use stable, unique IDs.

The service validates the required fields declared by the dataset and requires `provenance.source_uri` and `provenance.market` for every entry. Product and policy records should follow `rules.product_policy_requires`.

| Field | Requirement |
|---|---|
| `id` | Stable and unique; do not reuse an ID for a different fact. |
| `topic` | A concise normalized topic used for filtering/ranking. |
| `title` | Human-readable description of the entry. |
| `content` | A self-contained fact or recommendation. Keep unrelated facts separate. |
| `source` | A readable source label returned with search results. |
| `updated_at` | ISO date (`YYYY-MM-DD`) representing the last content review. |

Before adding a product, policy, or time-sensitive claim, capture and validate these provenance attributes:

- `source_type`, for example `official_web`, `official_pdf`, `internal_policy`, or `editorial_guidance`;
- `source_uri` or internal document identifier;
- publisher/owner and publication or revision identifier;
- `effective_from` and, where applicable, `expires_at`;
- market/locale and applicable model, model year, and trim;
- review status and reviewer/approver;
- retrieval timestamp for web content.

Do not add a claim when its authority or applicability cannot be established. Do not combine conflicting sources silently; retain both with their scope and escalate the conflict to the content owner. Split long documents into focused entries and preserve a pointer to the exact source section or page.

## Recommended production organization

The schema 2.0 JSON is suitable for the current repository-sized dataset. At larger scale, split it into typed source collections or move it to an indexed store while preserving the shared provenance contract:

- vehicle specifications and equipment: official product data, scoped by market/model year/trim;
- test-drive guidance: reviewed internal guidance with a named content owner;
- ownership, charging, maintenance, and warranty: current official documents and policies;
- live showroom and booking facts: database/service APIs;
- FAQ and policy: versioned official content with effective and review dates.

`KnowledgeService` filters market and known model/trim/model-year scope before lexical ranking. It suppresses rejected, superseded, expired, and overdue high-sensitivity records, and never returns `live_data_required=true` records as static facts. It remains lexical retrieval rather than semantic/vector search.
