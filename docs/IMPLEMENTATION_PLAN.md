# ContentOps implementation status

Last updated: 2026-08-16

## Product objective

Build a genuinely useful single-owner content operations tool and a portfolio-quality demonstration of advanced Python plus a modern TypeScript/cloud stack.

## Completed

- [x] Replace embedded model-provider generation with host-model MCP architecture.
- [x] Create a Python application-service boundary and repository protocol.
- [x] Implement idea/research capture, immutable versions, feedback, approval, archive, handoff, metrics, and export.
- [x] Add idempotency and audit events to every workflow mutation.
- [x] Add SQLite and Postgres adapters.
- [x] Add local mode and Supabase JWT owner authentication.
- [x] Expose FastAPI routes and 16 model-independent MCP tools.
- [x] Add the installable ContentOps skill with research, writing, review, and LinkedIn safety guidance.
- [x] Replace the prototype UI with an API-backed editorial workspace.
- [x] Add Supabase SSR auth, same-origin BFF, responsive UI, PWA shell, and workspace export.
- [x] Remove Gemini, mocks, localStorage, Tailwind, duplicate API clients, and migration-era documentation.
- [x] Pass Python tests/lint and frontend lint/type/tests/production build.

## External deployment work

- [ ] Provision the Supabase project, owner account, Postgres connection, and redirect URLs.
- [ ] Run the Postgres adapter against the provisioned database and capture a restore drill.
- [ ] Deploy the Python API and MCP endpoint with HTTPS and health monitoring.
- [ ] Deploy the Next.js app to Vercel.
- [ ] Connect the remote MCP endpoint in the target ChatGPT/Codex account.
- [ ] Execute and record the MCP evaluation set.
- [ ] Add Sentry/PostHog only after privacy settings and real product events are defined.

## Product validation

- [ ] Use ContentOps for at least ten real posts.
- [ ] Measure time from raw note to approved version.
- [ ] Record revision count and which writing-profile rules remain useful.
- [ ] Interview two additional creators before considering multi-user architecture.

## Explicitly out of scope

- direct LLM provider billing or prompt orchestration in the backend;
- LinkedIn scraping, browser automation, engagement automation, or unattended publishing;
- fabricated multi-tenancy before a real second-user requirement;
- LangGraph until a workflow requires resumable model execution outside the host.
