# LinkedIn Compliance and Integration Guardrails

Status: active product and engineering constraint

Last researched: 2026-08-03

Scope: personal professional-content workflow, MCP plugin, research, drafting, approval, scheduling, and optional LinkedIn integration

> This document is an engineering and product-risk analysis, not legal advice. LinkedIn terms, product access, permissions, and API versions can change. Re-check the linked primary sources before shipping or materially changing any LinkedIn-facing capability.

## Executive decision

The product may safely automate research, drafting, review, versioning, reminders, and approval outside LinkedIn. It must not automate the LinkedIn website, scrape LinkedIn, or implement engagement automation.

The default publishing workflow is:

```text
Approved draft
  -> copy/open handoff
  -> user reviews in LinkedIn
  -> user schedules with LinkedIn's native scheduler
  -> app records the external schedule manually
```

An official API-backed, user-initiated `Publish now` experiment may be evaluated later with LinkedIn OAuth and `w_member_social`. Unattended background publishing at a future time remains disabled unless the applicable LinkedIn terms or written LinkedIn approval clearly authorize that exact use case.

This distinction is necessary because LinkedIn currently documents both of the following:

- The self-service **Share on LinkedIn** product grants `w_member_social`, which allows an authenticated member to create a post from an application.
- The general LinkedIn API Terms prohibit using LinkedIn Content or APIs to automate posting on LinkedIn.

The dedicated share capability supports a user-initiated share flow, but the general prohibition makes unattended scheduled posting materially ambiguous. The project must not treat an OAuth scope as blanket permission for background automation.

Primary sources:

- [Getting Access to LinkedIn APIs](https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access)
- [Share on LinkedIn](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)
- [LinkedIn API Terms of Use](https://www.linkedin.com/legal/l/api-terms-of-use)

## Product policy matrix

| Capability | MVP decision | Reason |
| --- | --- | --- |
| Research the open web | Allowed | Uses public non-LinkedIn sources and the host model's web tools. |
| Research or scrape LinkedIn profiles/posts | Prohibited | LinkedIn forbids scraping and storing non-officially obtained LinkedIn content. |
| Generate a draft outside LinkedIn | Allowed | The user reviews the result before publication. |
| Store user-entered ideas and app-generated drafts | Allowed | These are provided by the user or created in the application, not imported from LinkedIn APIs. |
| Import the user's old posts by copy/paste or upload | Allowed with consent | The user supplies the data directly; record its provenance as `user_provided`. |
| Bulk-import LinkedIn posts by scraping | Prohibited | No browser automation, crawler, extension, or unofficial data provider. |
| Review and edit AI-generated text | Required | AI output may be inaccurate; LinkedIn places responsibility on the member. |
| Explicit approval before any publishing handoff | Required | Preserves user control and prevents unintended public actions. |
| Copy and open LinkedIn | Allowed | The user completes the action in LinkedIn. |
| Schedule in LinkedIn's native UI | Preferred | LinkedIn officially supports native scheduling. |
| User-clicked official API share | Compliance-gated experiment | Dedicated API supports posting, but terms and exact product behavior must be validated. |
| Background API publishing at `scheduled_at` | Disabled by default | General API Terms prohibit automated posting unless separately permitted. |
| Browser-based auto-posting | Prohibited | LinkedIn explicitly prohibits third-party software that automates its website. |
| Automated likes, comments, follows, connections, or messages | Prohibited | High abuse and account-restriction risk; outside the product purpose. |
| Engagement pods or artificial engagement prompts | Prohibited | LinkedIn disallows artificial engagement and repetitive spam. |
| Automatic analytics import | Deferred | Member analytics permissions and Community Management access may require vetting. |
| Manual metrics entry | Allowed | Avoids restricted read scopes and still supports product validation. |

## 1. Website automation and scraping

LinkedIn's User Agreement and help documentation prohibit unauthorized automated access and third-party software or browser extensions that scrape, modify, or automate activity on the LinkedIn website.

The project must therefore never:

- drive linkedin.com with Playwright, Selenium, Puppeteer, a browser extension, or computer-use automation;
- scrape member profiles, posts, feeds, comments, reactions, or analytics pages;
- ask the user for a LinkedIn username, password, session cookie, or copied browser token;
- use an unofficial scraping provider or dataset as an indirect workaround;
- automate likes, comments, invitations, follows, messages, reposts, or connection activity;
- bypass access controls, quotas, or account limitations.

This prohibition applies even if the automation is technically possible or limited to the project owner's own account.

Primary sources:

- [LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement)
- [Automated activity on LinkedIn](https://www.linkedin.com/help/linkedin/answer/a1340567/automated-activity-on-linkedin?lang=en)
- [LinkedIn API Terms of Use](https://www.linkedin.com/legal/l/api-terms-of-use)

### Research-source rule

Automated content research must use open-web sources such as official vendor documentation, company engineering blogs, research papers, reputable news outlets, RSS feeds, and user-provided URLs.

The research skill must exclude LinkedIn profiles, feeds, posts, and comments as ingestion sources. A search result pointing to LinkedIn may be shown to the user as a normal link, but its text must not be scraped, copied into the database, or used to build a writing profile.

## 2. Posting access is not the same as automation permission

### Open consumer permission

LinkedIn lists `w_member_social` under open consumer permissions through the self-service **Share on LinkedIn** product. It permits posting, commenting, and liking on behalf of an authenticated member. The Share on LinkedIn guide shows direct creation of text, URL, and image shares after OAuth authorization.

This is the appropriate scope to investigate for a personal, user-initiated share flow. It does not provide read access to the member's history or analytics.

### General API restriction

The current API Terms include a general restriction against using LinkedIn Content or APIs to automate posting. They also require editable pre-filled content and clear notice when an application prepares content for a user.

Product interpretation:

1. `Generate -> show editable preview -> explicit user click -> share` is the narrowest potentially supportable API flow.
2. `Approve now -> backend posts days later without another active user action` is not considered safe to ship without written confirmation or additional terms that explicitly cover scheduled automation.
3. The application must preserve a manual/native LinkedIn scheduling path even if an API integration is later approved.

### Required compliance gate before API publishing

Do not merge or enable LinkedIn publishing until all of the following are evidenced:

- the app is registered in the LinkedIn Developer Portal;
- the exact product and scopes are visible for that app;
- the OAuth consent screen accurately describes the action;
- the current API Terms and any additional product terms have been reviewed;
- a documented decision states whether user-initiated sharing is permitted for the intended flow;
- unattended scheduled publishing has written authorization if it is in scope;
- a real test call succeeds through the official API;
- a kill switch and manual fallback exist.

If the permission boundary remains ambiguous, the decision is **do not automate publication**.

## 3. Native LinkedIn scheduling

LinkedIn's own scheduler currently allows a member to choose an exact time between 10 minutes and 3 months in the future. LinkedIn documents that Events, Jobs, and Services posts are not supported by the native scheduler.

The MVP should use this as the publication handoff:

```text
App marks version approved
  -> user selects target time in the app for planning
  -> app copies the immutable approved version
  -> app opens LinkedIn
  -> user pastes and schedules with LinkedIn
  -> user records `scheduled_externally`
```

The app's calendar is a planning and tracking surface. It must not claim that a LinkedIn post is scheduled until the user confirms the native LinkedIn scheduling step.

Primary source: [Schedule posts on LinkedIn](https://www.linkedin.com/help/linkedin/answer/a1347212/schedule-posts?lang=en)

## 4. Community Management access became a major product constraint

The 2026 Community Management documentation requires developer vetting. LinkedIn currently states that this program is available only to registered legal organizations for commercial use cases. The review requires, among other things, a verified business email, legal organization details, a website, privacy policy, a verified company Page, and potentially a screencast and test credentials.

This means a personal portfolio project must not assume access to:

- member post analytics APIs;
- member feed management;
- comment/reaction management;
- social-action webhooks;
- organization management APIs.

Development tier limits documented by LinkedIn currently include:

- 500 calls per application per 24 hours;
- 100 calls per member of an application per 24 hours;
- no `BATCH_GET` calls;
- disabled Social Actions webhooks.

Standard-tier access requires a second review and is discretionary.

Primary sources:

- [Community Management App Review](https://learn.microsoft.com/en-us/linkedin/marketing/community-management-app-review?view=li-lms-2026-06)
- [Increasing Access](https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access?view=li-lms-2026-05)

### Product consequence

The MVP records performance metrics manually. Community Management analytics are an optional future capability, not a product dependency.

## 5. Rate limits and API reliability

LinkedIn applies both application-level and member-level daily quotas. Limits reset at midnight UTC. Exceeded limits return HTTP `429`. Standard endpoint quotas are not published as fixed documentation values; they must be inspected in the application's Developer Portal Analytics page after making a request.

Engineering requirements for any future LinkedIn client:

- centralize all LinkedIn calls behind one adapter;
- store no hard-coded assumption that a public quota is permanent;
- record response status and request correlation without logging tokens;
- handle `429` with bounded retry and next-reset scheduling;
- stop retrying permanent OAuth or permission failures;
- expose a circuit breaker/kill switch;
- alert before expected quota exhaustion when portal data is available;
- never create multiple apps to circumvent quotas.

Primary source: [LinkedIn API rate limiting](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)

## 6. Versioning and maintenance burden

LinkedIn Marketing APIs use explicit `LinkedIn-Version: YYYYMM` headers and the `/rest/` base path. A missing or sunset version causes errors. LinkedIn documents a minimum support window of one year and recommends regular migration.

Engineering requirements:

- keep the LinkedIn version in configuration, not scattered through code;
- add a scheduled monthly documentation check;
- test against the next supported version before switching;
- log the version used for every call;
- keep contract fixtures for the active version;
- treat `426 Upgrade Required` as an operational incident.

Primary source: [LinkedIn Marketing API versioning](https://learn.microsoft.com/en-us/linkedin/marketing/versioning?view=li-lms-2026-01)

## 7. Data storage, privacy, and deletion

LinkedIn API Content has strict storage restrictions. Where storage is permitted, it must be segregated, selectively deletable, limited to the necessary duration, and unavailable to unrelated users. LinkedIn permits storage of application-specific member identifiers and OAuth tokens, subject to security and deletion obligations.

The API Terms also require:

- a readily available user agreement and privacy policy;
- accurate disclosure of collection, use, storage, sharing, and deletion;
- legally valid consent before collecting a member's Content;
- deletion when the user requests it or closes the account;
- deletion of LinkedIn-derived Content and credentials after termination or loss of access;
- appropriate security, access control, encryption, logging, and incident handling.

### Provenance is mandatory

Every stored item must have a provenance value:

```text
user_provided
app_generated
open_web_source
linkedin_api
```

Rules:

- `user_provided` and `app_generated` content can form the writing-history dataset.
- `open_web_source` records store only necessary excerpts/metadata and source URLs, respecting copyright and privacy.
- `linkedin_api` data must live in a segregated repository boundary with retention and deletion controls.
- scraped or unofficial LinkedIn content has no valid provenance value because it must never be ingested.

The preferred way to build style memory is to store the exact drafts approved in this app or old posts that the user manually uploads. Do not read the member's entire LinkedIn history through automation.

Primary source: [LinkedIn API Terms of Use](https://www.linkedin.com/legal/l/api-terms-of-use)

## 8. AI-generated content and community quality

LinkedIn states that members remain responsible for AI-assisted content and should review it for accuracy, suitability, compliance, and whether it represents their own tone and knowledge. Its Professional Community Policies require authentic, accurate, original, relevant, and professional content and prohibit spam and artificial engagement.

The product must therefore enforce:

- human approval for every externally published version;
- source links for externally verifiable claims;
- no invented employment stories, results, clients, metrics, or personal experiences;
- no confidential employer, customer, university, or project details;
- no misleading claims presented as fact;
- no engagement bait, chain-letter patterns, reaction polls, or coordinated engagement suggestions;
- no gratuitously repetitive posts;
- a visible AI-assisted notice inside the app, without claiming LinkedIn endorsement;
- an editable preview before any share handoff.

Primary sources:

- [LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement)
- [Professional Community Policies](https://www.linkedin.com/legal/professional-community-policies)
- [High volume of content shared](https://www.linkedin.com/help/linkedin/answer/a1339697/high-volume-of-messages-sent?lang=en)
- [Spam policy](https://www.linkedin.com/help/linkedin/answer/a1338787)

### Internal cadence guardrail

LinkedIn does not publish a universal safe posting number. The personal MVP will therefore use a conservative internal default of at most one planned feed post per 24 hours and will not support bulk publishing. This is a product guardrail, not a claim that any fixed cadence guarantees account safety.

## 9. Naming and brand restrictions

For Community Management review, LinkedIn currently requires that an application name not include any portion of the LinkedIn or Microsoft names or logos. The API Terms also prohibit implying that the application is approved, verified, created, or endorsed by LinkedIn.

Consequences:

- `LinkedIn Content Creator` remains a historical repository name only.
- Choose a neutral product name before registering an app, for example `ContentOps Studio`, `DraftFlow`, or another verified available name.
- Do not use the LinkedIn logo in the product identity.
- Describe the integration factually as an optional publishing destination.
- Do not use phrases such as `official`, `LinkedIn-approved`, or `verified by LinkedIn`.

Primary sources:

- [Community Management App Review](https://learn.microsoft.com/en-us/linkedin/marketing/community-management-app-review?view=li-lms-2026-06)
- [LinkedIn API Terms of Use](https://www.linkedin.com/legal/l/api-terms-of-use)

## 10. Security rules for a future official integration

If API publishing passes the compliance gate:

1. Use LinkedIn OAuth 2.0; never accept passwords or cookies.
2. Request the minimum scope needed for the active capability.
3. Encrypt access and refresh tokens at rest.
4. Keep tokens server-side and out of MCP tool results, model context, logs, and browser storage.
5. Require an authenticated application user and enforce record ownership.
6. Bind publication to an immutable approved version and its content hash.
7. Make `Publish now` a separate explicit action from `Approve`.
8. Use an idempotency record even if the LinkedIn endpoint does not provide a native key.
9. Persist the returned post URN and a user-openable URL.
10. Provide disconnect and delete-account flows.
11. Disable the integration globally without redeployment.
12. Keep the manual/native scheduler fallback permanently available.

## 11. Required tests

### Policy tests

- The MCP skill refuses requests to scrape LinkedIn.
- The skill refuses automated likes, comments, invitations, messages, and engagement manipulation.
- Research prompts exclude LinkedIn member content as a source.
- Generated claims retain source URLs.
- A draft cannot move to `approved` without a user action.
- Editing an approved version invalidates the approval.
- A scheduled planning time is never presented as a confirmed LinkedIn schedule without user confirmation.

### Integration tests

- OAuth state and PKCE validation.
- Expired or revoked token behavior.
- Missing permission behavior.
- `401`, `403`, `426`, `429`, and `5xx` handling.
- Version-header contract.
- Duplicate-submit prevention.
- User data export and deletion.
- Kill-switch behavior.

### Human acceptance test

The reviewer must be able to see and edit the exact text that would be shared. Approval, scheduling intent, and actual publication must be distinct, auditable events.

## 12. Decision record

| Date | Decision |
| --- | --- |
| 2026-08-03 | No LinkedIn website automation or scraping. |
| 2026-08-03 | No automated likes, comments, connections, messages, or engagement behavior. |
| 2026-08-03 | Manual/native LinkedIn scheduling is the production-safe MVP. |
| 2026-08-03 | User-initiated API sharing is an experiment behind a compliance gate. |
| 2026-08-03 | Unattended scheduled API publishing is disabled without explicit authorization. |
| 2026-08-03 | Manual analytics entry is the MVP; Community Management analytics are optional. |
| 2026-08-03 | The product must be renamed before LinkedIn developer registration. |

## 13. Source review checklist

Revisit before each LinkedIn integration release:

- [ ] User Agreement reviewed.
- [ ] API Terms reviewed.
- [ ] Automated activity policy reviewed.
- [ ] Share on LinkedIn guide reviewed.
- [ ] Current access and permission table reviewed.
- [ ] Current rate limits inspected in Developer Portal.
- [ ] Current API version and sunset dates reviewed.
- [ ] Community Management eligibility checked if read/analytics features are planned.
- [ ] Privacy policy and deletion behavior match implementation.
- [ ] Product name and branding comply with the latest review rules.
