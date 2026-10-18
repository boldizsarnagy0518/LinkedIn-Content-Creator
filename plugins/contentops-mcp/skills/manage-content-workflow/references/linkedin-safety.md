# LinkedIn safety boundary

The MVP is draft-and-handoff, not unattended publishing.

- Never scrape LinkedIn or automate browser actions against LinkedIn.
- Never automate likes, comments, connection requests, follows, messages, or other engagement.
- Never store LinkedIn session cookies or ask the user for them.
- Never claim a post is scheduled or published from ContentOps state alone. Require the user's explicit confirmation that the action happened in LinkedIn's native interface.
- Require explicit user approval for the exact current draft before handoff.
- For scheduling, return the approved copy and recommended time, then use LinkedIn's native scheduler manually.
- Use `contentops_set_publication_plan` only for the current exactly approved version. Its `planned` state is internal and performs no network action.
- Use `contentops_confirm_external_schedule` only after explicit user confirmation of native scheduling.
- Use `contentops_mark_published` only after explicit user confirmation that the post is live.
- Treat a cancelled publication plan as stale. Never restore it without a fresh exact-version approval and new plan.

If a future official publishing integration is added, keep it behind separate authorization, a fresh confirmation step, an audit record, rate limits, and a kill switch. Re-check current LinkedIn terms and product access before enabling it.
