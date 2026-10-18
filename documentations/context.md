# ContentOps project context

Last updated: 2026-09-08

The primary personal workflow includes spontaneous walking notes: save only, or save and prepare a ChatGPT MCP draft request. The user explicitly chose host MCP usage with their existing ChatGPT subscription; do not add a model API provider or background model runner. See `docs/MCP_IDEA_WORKFLOW.md` for the implemented flow and verification boundaries.

## Goal

ContentOps is a useful private editorial system and a strong portfolio project. It should teach two complementary tracks:

1. Advanced Python: typed domain models, application services, repository ports, SQL persistence, FastAPI, MCP, authentication, testing, and deployment.
2. Modern product stack: TypeScript, React, Next.js, Supabase, Vercel, responsive product design, and production integration.

Python owns business rules and durable state. TypeScript owns the browser experience and its BFF. The host model, currently ChatGPT or Codex, owns research, reasoning, and writing.

## Product truth

The product's valuable object is not an AI-generated post. It is a traceable editorial decision:

```text
source -> immutable draft -> feedback -> exact approval -> human publication handoff -> observation
```

Every externally meaningful transition is explicit and auditable. Saving a new version invalidates approval and cancels the active publication plan. `planned`, `scheduled_externally`, and `published` are different facts.

## Current architecture

- Python 3.12, FastAPI, Pydantic, MCP Python SDK, psycopg, PyJWT, uv, pytest, Ruff
- TypeScript, React 19, Next.js 16, CSS Modules, Lucide
- SQLite for local work; Supabase Postgres and Auth for production
- Next.js same-origin BFF forwards the Supabase access token to FastAPI
- FastAPI and MCP use the same `ContentWorkflowService` and `ContentRepository`
- single-owner authorization via an exact Supabase user UUID

## Engineering rules

- Put workflow invariants in Python, not React or transport handlers.
- Depend on protocols at the application boundary.
- Treat API/MCP handlers as validation and mapping adapters.
- Every mutation is idempotent and emits an event.
- Draft versions are immutable; correction creates a new version.
- Approval binds current version ID and SHA-256 content hash.
- Never silently fall back between real and mock behavior.
- Do not add model-provider abstractions to the backend.
- Add LangGraph only for a demonstrated resumable model workflow; MCP tool sequences currently belong to the host.
- Keep local and production paths behaviorally equivalent.

## Frontend direction

The UI is an editorial control room, not a SaaS landing page. It uses a compact queue, paper-like manuscript, proofing labels, version rail, and review/publish inspector. Avoid generic gradient heroes, decorative card grids, oversized rounding, generic AI copy, and visual elements unrelated to the domain.

The first screen is the working application. Controls use recognizable icons and stable layouts. Mobile stacks the same workflow in priority order without hiding capability.

## Safety boundary

- No LinkedIn website automation or scraping.
- No automated likes, comments, follows, connections, or messages.
- No claim that an internal plan changed LinkedIn.
- LinkedIn-native scheduling is manually confirmed by the user.
- Performance metrics are user-entered observations.
- Research uses open-web sources and stores source URLs.

See `docs/LINKEDIN_COMPLIANCE.md` for the detailed and time-sensitive policy analysis.

## Next external milestone

Provision Supabase, run the real Postgres/auth smoke test, deploy Python and Next.js, then execute `docs/MCP_EVALUATION.md` in the target account. Product validation with real posts comes before multi-user scope or more infrastructure.
