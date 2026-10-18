# Architecture decision records

Last updated: 2026-08-16

## ADR 001: Host model, model-independent backend

**Decision:** ChatGPT or Codex performs research and writing. ContentOps stores workflow state and exposes MCP tools. The backend contains no Gemini, OpenAI, Anthropic, or other model-provider client.

**Why:** The differentiating value is durable human review and safe handoff, not another prompt wrapper. This also removes duplicate billing, provider lifecycle, and mock/live drift.

## ADR 002: Python application core

**Decision:** Python owns domain rules through `ContentWorkflowService` and a `ContentRepository` protocol. FastAPI and MCP are adapters.

**Why:** This keeps the owner's strongest language central, provides meaningful advanced-Python practice, and prevents transport-specific business logic.

## ADR 003: Immutable versions and exact approval

**Decision:** Material edits create immutable versions. Approval requires the current version ID and SHA-256 content hash. A new version or change request invalidates approval and cancels an active plan.

**Why:** Publishing the wrong revision is the central workflow risk. The data model makes that race explicit and testable.

## ADR 004: Human-controlled LinkedIn handoff

**Decision:** ContentOps records planning and explicit user confirmations, but does not operate LinkedIn. Native scheduling remains a user action.

**Why:** It is useful without crossing uncertain API terms or website-automation restrictions. See `docs/LINKEDIN_COMPLIANCE.md`.

## ADR 005: SQLite locally, Postgres in production

**Decision:** The repository port selects SQLite from a local path or Postgres from `CONTENTOPS_DATABASE_URL`.

**Why:** SQLite keeps development friction low. Supabase Postgres provides durable hosted storage without changing use cases.

## ADR 006: Single-owner Supabase authorization

**Decision:** Production accepts Supabase JWTs only when `sub` matches `CONTENTOPS_OWNER_USER_ID`. Local mode uses one local identity.

**Why:** The current product has one real user. Exact owner enforcement is safer than nominal multi-tenancy without complete row ownership and RLS.

## ADR 007: Thin Next.js application

**Decision:** The browser calls one typed client through `/api/workflow`; the BFF forwards the Supabase session to Python. React manages interaction state, not workflow invariants.

**Why:** It keeps secrets and backend topology out of the browser and avoids duplicate rules.

## ADR 008: Editorial visual system

**Decision:** The working interface uses a queue, manuscript, version rail, and inspector with CSS Modules. No Tailwind dependency, marketing landing page, gradient hero, or decorative card wall.

**Why:** The visual language should emerge from the product's editorial object model and feel authored, dense, and repeatable in daily work.

## ADR 009: Defer LangGraph and direct publishing

**Decision:** Do not add LangGraph until the product owns a resumable model execution loop. Do not add direct LinkedIn publishing until an official integration passes the documented compliance gate.

**Why:** Both would add complexity before a validated requirement. The current host-native tool sequence and manual handoff are simpler and safer.

## ADR 010: Explicit host handoff and guarded editing

**Decision:** Quick capture supports save-only and a copyable request for an existing ChatGPT MCP connection. The host performs model work and saves through MCP. The browser polls while visible and refreshes on focus. Account-scoped local working copies survive navigation, and new writers send `expected_current_version_id` to detect stale bases. SQLite immediate transactions and a single-owner Postgres advisory transaction lock serialize workflow mutations.

**Why:** The user wants to use their existing ChatGPT subscription. An app-owned model API would contradict that requirement. Explicit handoff reflects where execution actually starts, and optimistic version checks combined with atomic transactions prevent concurrent browser and host activity from silently overwriting editorial decisions.

## ADR 011: Hosted OAuth and one backend deployment

**Decision:** A combined ASGI factory mounts FastAPI at `/api` and the MCP application at the root so `/mcp` and protected-resource discovery retain their canonical paths. Both lifespans run. Supabase hosts OAuth authorization/token issuance; Next.js provides explicit owner-only consent and preserves the authorization request through login. A dedicated pre-registered client and access-token hook bind MCP tokens to the public MCP URL. Storage uses a private `contentops` schema. Production startup requires authenticated, durable configuration.

**Why:** A bearer-token verifier alone does not complete ChatGPT account linking. Separate audiences keep browser sessions distinct from MCP tokens, and a shared deployment reduces configuration drift between the two workflow surfaces. Account setup and the live OAuth acceptance test remain documented deployment steps, not assumed local test results.
