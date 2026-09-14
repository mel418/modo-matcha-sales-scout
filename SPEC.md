# Modo Matcha Sales Scout — Technical Specification

An autonomous B2B outbound sales agent for [Mōdō Matcha](https://modomatcha.com), a mobile
hand-whisked matcha bar and catering company serving Los Angeles and Orange County.

**Hackathon:** AWS "Agents for Humans" — *Professional Agents* track
**Built with:** Strands Agents SDK, deployed on Amazon Bedrock AgentCore Runtime
**Spec version:** 1.0 — 2026-09-01
**Target submission:** ~2026-09-13

---

## 1. Problem, user, and why it matters

### The problem

Mōdō Matcha books brand activations, corporate events, and weddings. Twelve brand partners in under
a year — Meta, Adobe, Benefit Cosmetics, Princess Polly, SEGA — is a strong track record. It's also,
honestly, almost entirely inbound: the majority of events start with someone reaching out first
— word of mouth, a referral from a past client, an agency who already knows the brand. There is no
real outbound motion today. Nobody is reading the LA business press for signals, nobody is reaching
out cold. Building that channel, well, is a daily grind with a narrow window:

1. Read enough of the LA business, retail, and beauty press to notice who just did something that
   implies an event — opened a store, closed a round, launched a product, hired an events producer.
2. Figure out whether they're actually a fit. LA presence? Right size? Do they run the kind of
   experiential moment a matcha cart belongs at? Have we already talked to them?
3. Find who to email and what their job title actually is.
4. Write something specific enough that it doesn't read like the fifteenth vendor email that week.

Steps 1–3 are search, reading, and bookkeeping. Step 4 is craft, but most of its inputs come from
1–3. Doing this well takes hours a week that a one-person shop running sales, production, and
delivery has never had spare — which is exactly why the channel has never been built, not because
it wouldn't work. And the sequence produces value only in its last five percent — the judgment call
of *"is this one worth sending?"*

### Who it's for

The owner, and every operator like them: a founder running a service business under about a dozen people
who is simultaneously the salesperson, the producer, the account manager, and — on event day — the
person hand-whisking matcha in front of ninety influencers. Outbound isn't a process she used to run
and let slip — it's a channel that was never built, because there was never a spare hour to build it.
Its absence shows up not as a missed task, but as a calendar that depends entirely on other people
remembering to call.

### Why it matters

This is exactly the shape of work the hackathon brief describes: routine, repetitive, individually
minor, collectively expensive. It's also work that *cannot* be automated by a dumb script, because
the fit judgment is genuinely hard — it takes reading a company's actual situation and knowing what
Mōdō Matcha is good at.

So the agent doesn't optimize a process that already exists — it builds the outbound motion this
business has never had time to build. It does the 95% that is search and reading, applies a rubric
that learns from the owner's real decisions as she starts making them, silently discards the leads
that don't clear the bar, and surfaces only the ones where a human decision creates value: *send
this, or don't.*

**It is not another app to check.** It runs at 6am whether or not anyone opens it. The dashboard
exists because approvals need somewhere to happen, not because the agent needs supervision.

---

## 2. What one run looks like

> **06:00 PT.** EventBridge fires. Nobody is awake.
>
> The **Scout** runs four search strategies against the last 72 hours of LA/OC business news and
> finds fourteen candidate organizations. Nine are already in DynamoDB — contacted, rejected, or
> mid-conversation — so they're dropped before a single token is spent on them. Five are new.
>
> For each of the five, the **Researcher** reads their site and recent coverage and assembles a
> profile: LA presence, industry, size band, what the actual event signal was, who the likely
> contact is, where the contact page lives. Every claim carries a source URL or is left null.
>
> The **Scorer** grades each against the ICP rubric — *and* against the seven rejection rationales
> the owner has written since the agent went live. Two score below the gate. They're marked
> `rejected_auto` and never cost a human a second of attention.
>
> Three survive. The **Writer** drafts each one: names the specific signal that triggered the
> outreach, cites the one case study most relevant to that segment, and respects the real lead-time
> math — if the event is in nine days, it doesn't offer a branded cart, because a branded cart takes
> fifteen business days.
>
> The **Critic** reads all three cold. One opens with a generic line and cites a wedding case study
> at a corporate prospect. It goes back once and comes out better. All three are written to DynamoDB
> as `awaiting_approval`.
>
> **08:30 PT.** The owner opens the dashboard over coffee. Three drafts. They approve two — SES sends
> them. They reject the third: *"agency, not the brand — they don't hold the activation budget."*
> That sentence is written to AgentCore Memory.
>
> **Tomorrow at 06:00,** the Scorer will know that.

Total human time: about four minutes. Total human decisions: three, all of them real ones.

---

## 3. Architecture

### 3.1 Component diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTONOMOUS PATH (no human)                          │
└─────────────────────────────────────────────────────────────────────────────┘

  EventBridge Scheduler
  cron(0 6 * * ? *)  America/Los_Angeles
          │
          ▼
  Dispatcher Lambda  ──────────── thin; 15-min timeout, botocore read_timeout=900
          │                        (see §3.3 — why this Lambda is not optional)
          │ InvokeAgentRuntime
          ▼
  ┌──────────────────────────────────────────────────────────┐
  │  Bedrock AgentCore Runtime  (ARM64 container)            │
  │  BedrockAgentCoreApp @app.entrypoint → pipeline.run()    │
  │                                                          │
  │   Scout ─► dedupe ─► ┌ per lead ──────────────────────┐  │
  │  (Sonnet)            │ Research ─► Score ─► gate ─►   │  │
  │                      │            Draft ─► Critic     │  │
  │                      └────────────────────────────────┘  │
  │                         (Sonnet)   (Opus)     (Opus)     │
  └──────────────────────────────────────────────────────────┘
       │            │             │              │
       ▼            ▼             ▼              ▼
   Tavily       Bedrock       DynamoDB      AgentCore
  search/       Opus 5 /    modo-scout-      Memory
  extract       Sonnet 5       leads      (preferences)

┌─────────────────────────────────────────────────────────────────────────────┐
│                      HUMAN PATH (the only way to send)                      │
└─────────────────────────────────────────────────────────────────────────────┘

  FastAPI + HTMX dashboard  (AWS App Runner, public HTTPS — the live demo link)
          │
          ├── reads ──► DynamoDB  (queue of awaiting_approval, sorted by score)
          │
          ├── APPROVE ──► mailer.py ──► SES ──► status=sent  + EVENT row
          │                  └─ allowlist + per-run cap enforced here
          │
          └── REJECT ───► status=rejected_human
                          └─► AgentCore Memory.create_event(rationale)
```

### 3.2 Why deterministic orchestration

The stage order is a real dependency chain. You cannot score a lead before researching it, and you
cannot draft before scoring. Handing that ordering to an LLM orchestrator buys no capability the
pipeline doesn't already have, and costs reliability, latency, and tokens.

So the split is:

- **Python owns control flow.** Which stage runs, in what order, how many times, what happens on
  failure, when to stop.
- **LLMs own judgment.** What counts as a buying signal, whether this company is a fit, what to say
  to them, whether the draft is good enough.

This is not a compromise for the deadline; it's the correct decomposition. It also has two
properties that matter enormously in a twelve-day build:

1. **Every stage is independently testable.** Each one is a pure function from a Pydantic input to a
   Pydantic output. `tests/fixtures/` holds cached Tavily responses, so the whole pipeline runs
   offline, deterministically, in seconds, with no API spend.
2. **The demo video can be recorded in one take.** There is no orchestrator that might decide to
   explore differently on camera.

The architecture diagram still shows five Strands agents. It shows arrows between them instead of a
boss above them.

### 3.3 The EventBridge trap (important — do not skip this)

EventBridge Scheduler supports `InvokeAgentRuntime` as a universal target, which makes
`Scheduler ──► AgentCore` look like the obvious wiring. **Do not do this.** Universal targets are
*synchronous* and time out around 30 seconds. A full pipeline run takes minutes. The observed
failure mode is the worst kind: the agent run **succeeds**, does all its work, writes all its rows —
and the schedule reports failure and pushes the invocation to the DLQ, so you spend a day debugging
a system that was never broken.

The dispatcher Lambda exists solely to hold the long connection: a 15-minute function timeout and a
botocore client configured with `read_timeout=900`, `connect_timeout=10`, `retries={"max_attempts": 0}`.

The pipeline is sized to finish inside that window (see §11 on `MAX_LEADS_PER_RUN`), and because it
checkpoints after every lead (§7), even a timeout is non-destructive — the next run resumes from
where it stopped.

---

## 4. Pipeline stages

All five agents are Strands `Agent` instances. All structured outputs go through
`agent.structured_output(Model, prompt)`, which registers the Pydantic model as a tool and validates
the result — no JSON parsing, no regex, no retry-on-malformed logic to write.

### 4.1 Scout

| | |
|---|---|
| **Model** | Sonnet 5 (`us.anthropic.claude-sonnet-5`) |
| **Tools** | `tavily_search` |
| **Input** | The strategy list from `config/search_strategies.yaml` |
| **Output** | `list[Candidate]` |
| **File** | `src/scout/agents/scout.py` |

```python
class Candidate(BaseModel):
    org_name: str
    domain: str | None = Field(None, description="Root domain, no scheme or www")
    signal_type: Literal["retail_opening", "funding", "product_launch",
                         "agency_activity", "hiring", "other"]
    signal_summary: str = Field(description="One sentence: what happened, when")
    signal_date: date | None
    source_url: HttpUrl
    geography_note: str | None = Field(None, description="Evidence of LA/OC presence, if any")
```

**Failure mode it guards against:** returning plausible-sounding companies that don't exist, or
signals with no date. Every candidate must carry a `source_url` the Researcher can actually open.
Candidates without one are dropped in Python, not argued with in the prompt.

**Prompt notes:** the system prompt states the geography constraint (LA + Orange County, broader
SoCal only for large events), the recency window (default 14 days, from config), and an explicit
instruction that returning six well-sourced candidates beats returning twenty guesses.

### 4.2 Researcher

| | |
|---|---|
| **Model** | Sonnet 5 |
| **Tools** | `tavily_search`, `tavily_extract` |
| **Input** | One `Candidate` |
| **Output** | `CompanyProfile` |
| **File** | `src/scout/agents/researcher.py` |

```python
class SourcedClaim(BaseModel):
    value: str
    source_url: HttpUrl

class CompanyProfile(BaseModel):
    org_name: str
    domain: str
    la_oc_presence: SourcedClaim | None
    industry: Literal["beauty", "wellness", "fashion", "food_bev", "tech",
                      "media", "agency", "professional_services", "other"]
    size_band: Literal["<50", "50-200", "200-1000", "1000+", "unknown"]
    event_evidence: list[SourcedClaim] = Field(
        description="Evidence this org runs the kind of event Modo Matcha serves")
    likely_contact_role: str | None
    contact_url: HttpUrl | None
    instagram_handle: str | None
    notes: str | None
```

**Failure mode it guards against:** invented headcounts and imagined LA offices. The `SourcedClaim`
wrapper makes fabrication structurally awkward — a claim without a URL cannot be represented. The
system prompt says plainly: **leave the field null rather than guess.** `size_band` has an explicit
`"unknown"` member for the same reason.

Sonnet 5 rather than Opus here because this stage is high-volume and mostly reading — it runs once
per candidate, and extraction is not where model quality shows up in the final email.

### 4.3 Scorer

| | |
|---|---|
| **Model** | Opus 5 (`us.anthropic.claude-opus-5`) |
| **Tools** | none — pure judgment on material already gathered |
| **Input** | `CompanyProfile` + `config/icp.yaml` + retrieved memories |
| **Output** | `FitScore` |
| **File** | `src/scout/agents/scorer.py` |

```python
class FitScore(BaseModel):
    score: int = Field(ge=0, le=100)
    tier: Literal["hot", "warm", "cool", "disqualified"]
    reasons: list[str] = Field(min_length=1, description="Why this score, citing profile evidence")
    disqualifiers: list[str] = Field(default_factory=list)
    recommended_service_line: Literal["brand_activation", "corporate", "wedding"] | None
    suggested_guest_count: int | None
    timing_note: str | None = Field(None, description="Lead-time feasibility given the signal date")
```

This is the stage where the system's accumulated judgment lives. Its prompt is assembled from three
sources: the static rubric in `config/icp.yaml`, the `CompanyProfile`, and the top-k relevant
memories retrieved from AgentCore Memory (§8) — the owner's own past rejection rationales, in their words.

**Failure mode it guards against:** scoring drift, and the rubric silently diverging from what the owner
actually believes. Every score must cite specific profile evidence in `reasons`, which makes a bad
score legible rather than mysterious.

### 4.4 The gate (pure Python — not an agent)

```python
if fit.tier == "disqualified" or fit.score < settings.SCORE_THRESHOLD:  # default 65
    store.mark(lead, status="rejected_auto", reason=fit.reasons)
    continue  # never reaches Writer or Critic
```

The single most important line in the system, for two reasons. It is the mechanism by which the
agent respects the human's attention — a bad lead costs the owner nothing, not even a glance. And it is
the largest cost lever in the whole pipeline, because everything downstream of it runs on Opus 5
(§11).

### 4.5 Writer

| | |
|---|---|
| **Model** | Opus 5 |
| **Tools** | none |
| **Input** | `CompanyProfile` + `FitScore` + `config/proof_points.yaml` + `config/business.yaml` |
| **Output** | `Draft` |
| **File** | `src/scout/agents/writer.py` |

```python
class Draft(BaseModel):
    subject: str = Field(max_length=80)
    body: str
    cited_signal_url: HttpUrl
    proof_point_used: str = Field(description="Key of the case study cited, from proof_points.yaml")
    service_line: Literal["brand_activation", "corporate", "wedding"]
```

Hard requirements, stated in the system prompt and enforced by the Critic:

- **Name the specific signal.** "Saw you're opening on Abbot Kinney next month" — not "I came across
  your brand."
- **Cite exactly one proof point**, chosen for segment fit. Benefit × Love Wellness for beauty and
  influencer activations. Grant Thornton for corporate and office teams. Bel-Air Bay Club for
  weddings. The client roster (Meta, Adobe, SEGA, Princess Polly) is available as social proof.
- **Respect the lead-time math.** Branded cart = 15 business days, branded cups = 10 business days,
  so a fully branded activation needs ≥3 weeks. If the signal date puts the event inside that
  window, the draft must offer the unbranded experience instead. This rule comes from
  `config/business.yaml`, not from the model's memory.
- **Never quote a price.** Mōdō Matcha quotes per event after learning date, guest count, and venue.
  The email's call to action is to share those three things.
- **Under 150 words.** Mōdō Matcha's own booking funnel is three steps; the email should read like the
  first one.

### 4.6 Critic

| | |
|---|---|
| **Model** | Opus 5 |
| **Tools** | none |
| **Input** | `Draft` + `CompanyProfile` + `FitScore` + the same config |
| **Output** | `CritiqueResult` |
| **File** | `src/scout/agents/critic.py` |

```python
class CritiqueResult(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    revised_subject: str | None
    revised_body: str | None
```

Exactly **one** revision loop — if the revision still fails, the draft is stored with
`critic_issues` attached and shown to the owner flagged rather than hidden. A human seeing a flawed draft
labelled *"the critic wasn't happy with the opener"* is more useful than an empty queue.

The critic checks: generic opener; any factual claim not traceable to the profile; wrong service line
for the segment; lead-time violation; a price appearing anywhere; over 150 words; a proof point that
doesn't match the prospect's segment.

**Why a separate agent rather than a longer Writer prompt:** a model reviewing its own output in the
same turn is measurably worse at catching its own generic phrasing. A fresh context reading the draft
cold catches what the author cannot see.

---

## 5. Signals hunted

Three families, expressed in `config/search_strategies.yaml` as parameterized Tavily queries. Each
strategy carries a `topic`, a `time_range`, and domain hints.

**A. New LA/OC retail openings and pop-ups.** A store opening needs a launch moment, and a launch
moment needs something photogenic on a cart. Searches retail trade press and LA local business news
for openings, showrooms, and pop-up announcements in the service area.

**B. Funding rounds and dated product launches.** A recently-funded consumer brand with an LA
presence has both budget and a reason to celebrate; a dated product launch is a calendar entry with
a guest list attached. Both are reliable activation triggers and both are well covered in the press.

**C. Experiential agencies and event-producer hiring signals.** Two sub-strategies. Agencies running
LA activations are the buyer for a large share of Mōdō Matcha's existing work — Golin for Adobe,
Hello Roma Creative for Innisfree — so agencies are prospects in their own right. And a company
posting an events-producer role, or announcing a large new-hire class, is telegraphing internal event
volume. That second pattern is exactly the Grant Thornton case study, run in reverse.

**Instagram signals** are specified behind a tool interface (`src/scout/tools/social.py`) with a
fixture-backed implementation. Public social data is the highest-signal source for this specific
business — the following list on @modomatcha is essentially a client roster — but scraping it is
rate-limited and ToS-gray. The interface exists so a compliant data source can be dropped in later;
the shipped implementation reads fixtures and is clearly labelled as such in the README. **Nothing
in the demo depends on it.**

---

## 6. Business knowledge lives in config, not code

Nothing about Mōdō Matcha is hardcoded in Python. Four YAML files under `config/`:

**`business.yaml`** — service area (LA + OC; broader SoCal with travel fee); lead times (branded
cups 10 business days, branded cart 15, therefore ≥3 weeks for branded activations); deposit terms
(50%, non-refundable); balance due 3 days prior; cancellation policy (written notice ≥7 days,
weather non-refundable); setup requirements (~8'×8' footprint, dedicated-circuit power, elevator
access, no water hookup needed); dietary facts (organic, seed-oil free, A2 milk, gum-free oat milk,
non-caffeinated fruit-purée options); no tastings offered; COI available on request.

**`proof_points.yaml`** — the three case studies (Benefit × Love Wellness, Grant Thornton, Bel-Air
Bay Club) each tagged with the segments they suit; the four testimonials (Princess Polly, Benefit,
SEGA, NAOS) with attributed roles; the client roster; the "twelve brand partners in under a year"
line.

**`icp.yaml`** — the scoring rubric: weighted criteria, tier thresholds, and hard disqualifiers.

**`search_strategies.yaml`** — the queries from §5.

This is also what makes the *"generalizes to any local service business"* claim credible rather than
aspirational. Swap the four YAML files and the same pipeline prospects for a photographer, a florist,
or a mobile bartending company. The README should demonstrate this with a second config directory.

### Questions for the owner (turns the rubric from guesswork into ground truth)

The rubric ships with defensible defaults derived from the public site, so this does not block
starting. But these five answers are what make it *hers*:

1. Of the twelve brand partners, which came inbound versus outbound? The outbound ones are the
   template for what the Scout should be hunting.
2. Typical guest-count and price bands per service line — needed for `suggested_guest_count` to be
   meaningful and for the gate threshold to reflect real economics.
3. **The last few leads she turned down, and why.** The single highest-value input. These become the
   seed memories in AgentCore Memory and the `disqualifiers` list in `icp.yaml`.
4. Who actually signs off — brand manager, office manager, or the agency's producer? This determines
   `likely_contact_role` and the register the Writer uses.
5. Which case study lands best with which segment, in her experience. Currently inferred; better
   confirmed.

---

## 7. Data model

Single DynamoDB table, `modo-scout-leads`, on-demand billing.

| | |
|---|---|
| **PK** | `LEAD#<normalized_domain>` |
| **SK** | `META` \| `DRAFT#<iso8601>` \| `EVENT#<iso8601>` |
| **GSI1** | PK `STATUS#<status>`, SK `<zero-padded score>#<domain>` |

`META` holds the profile, score, status, and timestamps. `DRAFT#` rows are append-only draft
versions (original and critic revision both kept — useful in the demo video). `EVENT#` rows are the
append-only audit trail: discovered, researched, scored, gated, drafted, critiqued, approved, sent,
rejected.

**Statuses:**

```
discovered ─► researched ─► scored ─┬─► rejected_auto        (agent decided)
                                    └─► awaiting_approval ─┬─► sent            (human approved)
                                                           └─► rejected_human  (human declined)
```

**Domain-keyed PK is the dedupe mechanism.** Normalization (strip scheme, `www.`, trailing slash,
lowercase) lives in one function, `store.normalize_domain()`, and is unit-tested. This is what
guarantees the agent never emails the same company twice — the single most embarrassing failure mode
an outbound agent has.

GSI1 serves the dashboard queue in one query: everything `awaiting_approval`, highest score first.

**Checkpointing:** the pipeline writes after *every* stage of *every* lead, never batching at the
end. A run that dies at lead 7 of 10 has fully persisted leads 1–6, and the next run picks up the
partials by status rather than restarting. This is what makes the Lambda's 15-minute ceiling a
non-issue instead of a cliff.

---

## 8. Memory

AgentCore Memory holds one thing: **the owner's judgment, in their own words.**

When she rejects a draft in the dashboard she gives a one-line reason. That reason is written via
`create_event` against a single actor id (`owner`) with a stable session id per month. Long-term
semantic memory strategies extract the durable version of it.

On each subsequent run, the Scorer retrieves the top-k memories relevant to the current
`CompanyProfile` and includes them in its prompt under an explicit heading:

```
## What the owner has told you before
- "Agencies without the activation budget aren't worth it — go to the brand."
- "Anything under 50 people isn't worth the travel unless it's downtown."
```

The system gets better at the owner's job by watching the owner do the owner's job. That is the strongest thing
in the pitch, and it costs one text field in the dashboard.

Wrapped in `src/scout/memory.py` behind a two-method interface (`remember(text)`,
`recall(query, k)`).

**Fallback (this is first on the cut list):** a `DynamoDBPreferenceStore` implementing the same
interface — rejection reasons as rows, `recall()` returns the most recent N. Loses semantic
retrieval, keeps the learning behavior, costs about an hour. Because both sit behind the same
interface, the swap is one line in `settings.py` and nothing else in the codebase changes.

---

## 9. Human-in-the-loop contract

**The dashboard is the only path to a send.** Stated as invariants, each enforced in code rather
than in a prompt:

1. **No email leaves without an explicit approval write.** `mailer.send()` re-reads the lead from
   DynamoDB and refuses unless status is `awaiting_approval` and an approval record exists. The
   agent has no code path to SES at all — `mailer.py` is imported by the dashboard, never by the
   pipeline.
2. **Recipient allowlist**, enforced in `mailer.py` from `SES_ALLOWLIST`, independent of and in
   addition to SES sandbox restrictions. Two independent controls, because one is a config value and
   the other is an AWS account setting, and neither should be the only thing standing between a
   prototype and a stranger's inbox.
3. **Per-run send cap** (`MAX_SENDS_PER_DAY`, default 10), counted from `EVENT#` rows.
4. **Every send appended to the audit trail** with the exact body sent, message id, and timestamp.

### On real sending

SES is in **sandbox** on this account (`ProductionAccessEnabled: false`), with zero verified
identities today. Demo sends therefore go only to addresses verified in advance — the owner's, the
builder's, and a couple of test inboxes.

**This is a deliberate scope decision, not a limitation to apologize for.** The agent drafts real
emails to real researched prospects and shows them in full; only the delivery is routed to the
sandbox. The demo is identical either way.

Going live later is a *policy* decision rather than a code change: SES production access, a verified
sending domain with DKIM, bounce and complaint handling, CAN-SPAM compliance including a physical
address and working opt-out, and a considered position on cold-emailing strangers under Mōdō
Matcha's own domain reputation. The README says exactly this.

---

## 10. Repository layout

```
modo-matcha-sales-scout/
├── README.md                     # problem, quickstart, architecture, live demo link
├── SPEC.md                       # this file
├── LICENSE                       # MIT — must also be set in the GitHub About section
├── ARCHITECTURE.md
├── pyproject.toml
├── requirements.txt              # what CodeBuild installs into the ARM64 image
├── .env.example
├── bedrock_agentcore.yaml        # generated by `agentcore configure`
│
├── config/
│   ├── business.yaml
│   ├── proof_points.yaml
│   ├── icp.yaml
│   ├── search_strategies.yaml
│   └── demo_tenant/              # second config set — proves the generalization claim
│
├── src/scout/
│   ├── settings.py               # pydantic-settings; all env config, one place
│   ├── models.py                 # every Pydantic model in §4
│   ├── store.py                  # DynamoDB repository + normalize_domain()
│   ├── memory.py                 # AgentCore Memory + DynamoDB fallback, one interface
│   ├── mailer.py                 # SES + allowlist + cap. NOT imported by the pipeline.
│   ├── pipeline.py               # deterministic orchestration — the spine
│   ├── runtime.py                # BedrockAgentCoreApp entrypoint
│   ├── tools/
│   │   └── social.py             # Instagram interface, fixture-backed
│   └── agents/
│       ├── scout.py  researcher.py  scorer.py  writer.py  critic.py
│       └── _base.py              # shared BedrockModel construction, model tier constants
│
├── src/dashboard/
│   ├── app.py                    # FastAPI
│   ├── templates/                # Jinja2 + HTMX
│   └── static/
│
├── infra/
│   ├── template.yaml             # CloudFormation: DynamoDB, Lambda, Scheduler, IAM, App Runner
│   └── deploy.ps1 / deploy.sh
│
├── tests/
│   ├── fixtures/                 # cached Tavily + Bedrock responses — offline, deterministic
│   ├── test_store.py             # dedupe / normalization
│   ├── test_pipeline.py          # full run against fixtures
│   ├── test_gate.py
│   └── test_mailer_guards.py     # allowlist + approval invariants
│
└── scripts/
    ├── verify_ses.py             # verify demo recipient identities
    ├── seed_memories.py          # load the owner's past rejections
    └── run_local.py              # pipeline without AgentCore, against fixtures or live
```

---

## 11. Cost model

**Pricing caveat:** AWS's public Bedrock pricing page does not yet list Opus 5 or Sonnet 5 rates.
The figures below use Anthropic's first-party rates as the planning estimate — **Opus 5 at
$5/$25 per million input/output tokens, Sonnet 5 at $2/$10** — and must be confirmed against the
Bedrock console before relying on them. Bedrock is partner-priced and may differ.

Per run, at `MAX_LEADS_PER_RUN = 10` with roughly 4 clearing the gate:

| Stage | Model | Calls | Est. in / out | Est. cost |
|---|---|---|---|---|
| Scout | Sonnet 5 | 1 (multi-turn) | 25K / 3K | $0.08 |
| Researcher | Sonnet 5 | 10 | 15K / 1K each | $0.40 |
| Scorer | Opus 5 | 10 | 4K / 0.8K each | $0.40 |
| Writer | Opus 5 | 4 | 5K / 1K each | $0.20 |
| Critic | Opus 5 | 4 | 6K / 1K each | $0.22 |
| | | | **subtotal** | **~$1.30** |

Opus 5 runs adaptive thinking by default and thinking tokens bill as output, so **budget ~$2.00 per
run** as the realistic figure.

**Twelve-day projection:** 12 daily runs ≈ $24, plus development and test runs. App Runner at the
smallest size runs roughly $5–10 for the period. DynamoDB on-demand at this volume is effectively
free. Tavily's free tier (1,000 credits/month) comfortably covers it. AgentCore Runtime adds
consumption charges on top.

**Total: roughly $35–45 against the $50 credit. That is tight.** Three disciplines keep it safe:

- **Iterate against fixtures, not the live API.** The offline test suite is the cost control, not
  just a quality one.
- **Run every other day during development**, daily only in the final stretch.
- **Start at `MAX_LEADS_PER_RUN = 6`** and raise it only once the pipeline is stable.

**Cost knobs, in order of leverage:**

1. **`SCORE_THRESHOLD`** — the gate is the biggest lever by a wide margin, because every rejected
   lead skips both Opus stages. Raising it from 65 to 75 cuts Writer and Critic volume roughly in
   half.
2. `MAX_LEADS_PER_RUN` — caps Researcher and Scorer linearly.
3. Run frequency.
4. Model tier per stage — one constant per agent in `agents/_base.py`, trivially adjustable.
5. Reasoning effort on the Opus stages, if needed, via `BedrockModel(additional_request_fields=...)`.
   **Verify the exact parameter shape against the Strands docs before relying on it** — it is not
   confirmed in this spec.

---

## 12. Twelve-day schedule

**Days 1–2 — Foundation.**
Upgrade the AWS CLI (2.27 has no `bedrock-agentcore` commands — hard blocker). Repo, MIT license,
`pyproject.toml`. Install `strands-agents`, `strands-agents-tools`, `bedrock-agentcore`,
`bedrock-agentcore-starter-toolkit`. Tavily key. Confirm Bedrock model access with a one-line
`BedrockModel` call against `us.anthropic.claude-sonnet-5`. Write all four config YAMLs and every
Pydantic model in `models.py`. Send the owner the five questions from §6.

**Days 3–4 — Pipeline, local, offline.**
All five agents. `store.py` + DynamoDB table. `pipeline.py`. Capture Tavily fixtures on the first
live run, then develop against them.
🎯 **Milestone: `python scripts/run_local.py` produces real drafts from real leads.** This is the
project's spine. Everything after is deployment and presentation.

**Days 5–7 — Deploy.**
`runtime.py` with `@app.entrypoint`. `agentcore configure -e src/scout/runtime.py`, then
`agentcore launch` (CodeBuild builds ARM64 in the cloud — **no local Docker needed**, which matters
on Windows). Dispatcher Lambda with the long read timeout. EventBridge Scheduler. AgentCore Memory
with seeded rejections.
🎯 **Milestone: it runs at 6am with nobody watching.**

**Days 8–9 — Human surface.**
FastAPI + HTMX dashboard: approval queue sorted by score, draft with the cited signal and profile
evidence visible, approve / edit / reject with reason. `mailer.py` with both guards. Verify SES
identities. Deploy to App Runner.
🎯 **Milestone: live public URL, full loop closed.**

**⚠️ Day 9 is the decision point.** If behind, cut in this order: AgentCore Memory → critic → SES.
**Never cut the schedule** — "runs quietly in the background" is the premise of the entire brief.

**Days 10–12 — Submission.**
Architecture diagram. README with quickstart, the generalization demo, and the honest note on SES
sandbox. Demo video ≤5 min covering problem / who it's for / why it matters, with a real run on
screen. AWS Builder ID. The builder.aws.com post with "Agents for Humans" in the title. **Submit on
day 11, not day 12** — leave a full day of slack.

---

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| AgentCore quota or regional surprise | Blocks the deployment story | Test `agentcore launch` on day 5, not day 9. Fallback is Lambda + EventBridge, which forfeits the AgentCore score but keeps every other claim intact. |
| Tavily results thin on a narrow LA niche | Weak leads → weak demo | Four independent strategies rather than one. Fixtures captured early guarantee the demo works regardless of what Tavily returns on the day. |
| EventBridge synchronous-target timeout | A day lost debugging a working system | Already designed around (§3.3). Dispatcher Lambda from the start. |
| ARM64 build friction on Windows | Deploy blocked | Default `agentcore launch` uses CodeBuild — no local Docker. Do not use `--local-build`. |
| SES verification lead time | Can't demo the send | Verify identities on day 1. It's a two-minute task with an email round-trip. |
| Credits exhausted before submission | Can't run the demo | Fixture-first development, `MAX_LEADS_PER_RUN=6`, every-other-day runs. Set an AWS budget alert at $35 on day 1. |
| Opus 5 thinking tokens double the estimate | Budget overrun | Cost knobs in §11, ordered by leverage. Watch actual spend after the first three live runs. |
| The owner's answers arrive late | Rubric stays generic | Defaults ship on day 2 and are tunable to the last day — the rubric is a YAML file, not code. |

---

## 14. Submission checklist

- [ ] Public GitHub repo, all source, assets, and setup instructions
- [ ] **MIT license visible in the repo's About section** (not just a `LICENSE` file — the rules say About)
- [ ] README: what it does, who it's for, how it works, quickstart
- [ ] Architecture diagram
- [ ] Demo video ≤ 5 minutes — working project + pitch covering (1) the problem, (2) who it's for, (3) why it matters
- [ ] Text description of the project
- [ ] AWS Builder ID
- [ ] Live demo link (App Runner URL) — scores higher on Technical Implementation
- [ ] Track: **Professional Agents**
- [ ] *Bonus:* builder.aws.com post, publicly published before the deadline, with **"Agents for Humans"** in the title

---

## Appendix A — Verified SDK surface

Every symbol below was confirmed against current documentation on 2026-09-01. **Do not substitute
remembered API shapes for these.**

```bash
pip install strands-agents strands-agents-tools bedrock-agentcore bedrock-agentcore-starter-toolkit
```

```python
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools.tavily import tavily_search, tavily_extract   # env: TAVILY_API_KEY
from bedrock_agentcore.runtime import BedrockAgentCoreApp

model = BedrockModel(
    model_id="us.anthropic.claude-opus-5",   # inference-profile id, `us.` prefix
    region_name="us-east-1",
    temperature=0.3,
)
agent = Agent(model=model, tools=[tavily_search], system_prompt=SYSTEM)

result = agent.structured_output(FitScore, prompt)   # returns a validated FitScore

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    return {"result": pipeline.run(mode=payload.get("mode", "daily"))}

if __name__ == "__main__":
    app.run()      # POST /invocations, GET /ping, port 8080
```

**Deploy:**

```bash
agentcore configure -e src/scout/runtime.py    # writes bedrock_agentcore.yaml
agentcore launch                                # CodeBuild → ARM64 image → Runtime. No local Docker.
agentcore invoke '{"mode": "daily"}'
```

**Invoke from the dispatcher Lambda:**

```python
client = boto3.client(
    "bedrock-agentcore",
    config=Config(read_timeout=900, connect_timeout=10, retries={"max_attempts": 0}),
)
client.invoke_agent_runtime(
    agentRuntimeArn=ARN,
    runtimeSessionId=session_id,
    payload=json.dumps({"mode": "daily"}).encode(),
)
```

## Appendix B — Verified environment

| Fact | Value |
|---|---|
| AWS account | `385122037268` |
| Region | `us-east-1` |
| IAM | `cloud-learning-user`, **AdministratorAccess** — no permission blockers |
| Python | 3.12.7 |
| Node | v24.14.0 |
| AWS CLI | **2.27.49 — too old.** No `bedrock-agentcore` commands. Upgrade required. |
| SES | `SendingEnabled: true`, `ProductionAccessEnabled: false`, **0 verified identities** |
| Bedrock profiles confirmed | `us.anthropic.claude-opus-5`, `us.anthropic.claude-sonnet-5`, `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

## Appendix C — Open items

1. **Bedrock pricing for Opus 5 / Sonnet 5** — not on the public pricing page. Confirm in the console
   before trusting §11.
2. **Reasoning-effort parameter shape** for `BedrockModel` — the cost knob in §11 item 5 is
   unverified. Check the Strands model-provider docs before using it.
3. **The owner's five answers** (§6) — defaults ship without them; the rubric improves materially with them.
4. **Bedrock model access** — inference profiles exist in the account, but per-model access has not
   been exercised. One live call on day 1 settles it.
