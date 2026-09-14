# Modo Matcha Sales Scout

An autonomous B2B outbound sales agent for [Mōdō Matcha](https://modomatcha.com), a mobile
hand-whisked matcha bar and catering company serving Los Angeles and Orange County.

Built with the [Strands Agents SDK](https://strandsagents.com), running on
[Amazon Bedrock](https://aws.amazon.com/bedrock/).

**AWS "Agents for Humans" Hackathon — Professional Agents track.**

---

## The problem

Mōdō Matcha books brand activations, corporate events, and weddings — twelve brand partners
(Meta, Adobe, Benefit Cosmetics, Princess Polly, SEGA, and more) in under a year of operating.
The bottleneck isn't the pitch — it's finding out who needs one. Every week someone has to read
LA business and beauty press, notice who just did something that implies an event (a store
opening, a funding round, a product launch), judge whether they're a real fit, find the right
contact, and write something specific enough not to read like the fifteenth vendor email that
week. That's hours of work whose only real value is the last step: deciding *"is this one worth
sending?"*

## Who it's for

Casey, and every operator like her — a founder running a service business under a dozen people
who is simultaneously the salesperson, the producer, and (on event day) the person hand-whisking
matcha in front of ninety influencers. Prospecting is the first thing that falls off the list
when a week gets busy.

## What this agent does

Given a research pass over live web search, it:

1. Finds a real company with a live Los Angeles/Orange County event signal — a store opening,
   a funding round, a product launch, an experiential agency's campaign.
2. Verifies the signal against a real, working source URL — it will not invent a company.
3. Scores the fit against Mōdō Matcha's actual business (service lines, lead times, the client
   roster, past case studies).
4. Drafts a first-touch outreach email that names the specific signal, cites the one case study
   that matches the prospect's segment, and respects the real lead-time math (a fully branded
   cart needs 15 business days — an email should never promise one for an event happening sooner).

Run it and it hands you a complete pitch — company, evidence, score, reasoning, and a
ready-to-send email — instead of a page of search results you'd have to read yourself.

## Quickstart

```bash
git clone https://github.com/mel418/modo-matcha-sales-scout.git
cd modo-matcha-sales-scout
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell — use source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create `.env` (see `.env.example`):

```dotenv
TAVILY_API_KEY=tvly-your-key-here    # free tier at https://app.tavily.com
AWS_REGION=us-east-1
```

Configure AWS credentials with Bedrock access (`aws configure`), then confirm model access with:

```bash
python scripts/hello_bedrock.py
```

Run the agent:

```bash
python -m src.scout.demo_agent
```

A sample real run (unedited, live search + live Bedrock) is saved at
[`tests/fixtures/sample_run_erewhon.txt`](tests/fixtures/sample_run_erewhon.txt).

## What's built vs. what's designed

This submission ships the **core judgment loop as a single Strands agent** (research with a live
search tool, then structure the findings into a scored, drafted pitch) — built and tested against
real search results and a real Bedrock model, not mocked.

The full production design — five specialized agents (Scout, Researcher, Scorer, Writer, Critic)
chained by a deterministic pipeline, deployed on **Bedrock AgentCore Runtime**, with
**DynamoDB** for lead tracking and dedupe, **AgentCore Memory** so the agent learns from real
rejections over time, a human-approval dashboard, and **SES** for sending — is fully specified in
[`SPEC.md`](SPEC.md). That document also covers the reasoning behind a deterministic pipeline over
a single agent (the stage order is a real dependency chain — Python should own control flow,
models should own judgment), the cost model, and a day-by-day build schedule.

**Why the gap:** this build happened in a compressed window. The single-agent version proves the
hardest and highest-risk part of the idea — that an LLM can genuinely find, verify, and pitch a
real prospect end to end — without the deployment scaffolding around it. The hackathon rules note
AgentCore deployment strengthens (but does not require) the technical score; the architecture
below shows the intended target.

## Architecture

**What's running today:**

```
 you ──► python -m src.scout.demo_agent
              │
              ├─► Research agent (Strands + Bedrock, tavily_search tool)
              │      "find a real LA/OC prospect with a live event signal"
              │
              └─► Structuring agent (Strands + Bedrock, structured output)
                     "score this against Modo Matcha's ICP, draft the email"
```

**What's designed** (full detail in [`SPEC.md`](SPEC.md) §3–§9):

```
EventBridge Scheduler (daily, 6am PT)
        │
        ▼
Dispatcher Lambda ──► Bedrock AgentCore Runtime
                            │
                Scout ─► dedupe ─► [per lead] Research ─► Score ─► gate ─►
                                                          Draft ─► Critic
                            │              │                  │
                        Tavily          DynamoDB       AgentCore Memory
                     (search/extract)  (leads, audit)  (learned preferences)
                                             │
                                             ▼
                          FastAPI + HTMX dashboard (App Runner)
                          approve ──► SES send   |   reject ──► memory
```

## Configuration knowledge

Business facts (service lines, lead times, case studies, client roster) are currently inlined in
[`src/scout/demo_agent.py`](src/scout/demo_agent.py) for build-speed reasons. The full spec
(§6) calls for these to live in standalone `config/*.yaml` files so the same agent generalizes to
any local service business by swapping config — that refactor is the first item on the roadmap.

## Tech stack

- [Strands Agents SDK](https://strandsagents.com) — agent loop, tool use, structured output
- [Amazon Bedrock](https://aws.amazon.com/bedrock/) (Claude, via inference profiles)
- [Tavily](https://tavily.com) — live web search built for LLM agents
- Python 3.12, Pydantic

## License

MIT — see [`LICENSE`](LICENSE).
