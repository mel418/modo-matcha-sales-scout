# Devpost submission — copy/paste draft

Fill in the brackets, paste into the Devpost form. Don't overthink wording under time
pressure — this is already honest and complete; polish is not worth spending minutes on.

---

## Project name

**Modo Matcha Sales Scout**

## Elevator pitch (one line, if the form asks)

An autonomous sales agent that finds real Los Angeles brands about to need an event,
verifies the signal, and drafts the outreach email — giving a one-person catering business
an outbound motion it's never had time to build.

## Track

Professional Agents

## Text description

**The problem.** Mōdō Matcha is a mobile matcha-bar catering company that's booked twelve
brand partners — Meta, Adobe, Benefit Cosmetics, Princess Polly, SEGA — in under a year.
That track record is almost entirely inbound — the majority of events start with someone
reaching out first. There's no real outbound motion today: nobody is reading LA business and
beauty press for signals, noticing who just opened a store or launched a product, judging fit,
finding the right contact, and writing something specific enough not to sound like the
fifteenth vendor email that week. That's hours of work a one-person shop has never had time
to spend building, and its only real value shows up in the very last step anyway — deciding
whether it's worth sending.

**Who it's for.** The owner, and every operator like them: a founder running a service business
under a dozen people, doing sales, production, and delivery herself. Outbound isn't a process
that fell off her plate — it's a channel that's never existed, because there was never a spare
hour to build it, and its absence shows up as a calendar that depends entirely on other people
remembering to call.

**How it works.** Built on the Strands Agents SDK against Amazon Bedrock. A research agent
uses live web search to find one real company with a genuine LA/Orange County event signal
— a store opening, a funding round, a product launch — and verifies it against a real
source URL rather than inventing one. A second agent scores the fit against Mōdō Matcha's
actual business (service lines, real lead-time constraints, past case studies, client
roster) and drafts a first-touch email that cites the one case study matching the
prospect's segment.

This submission's core loop is real: live search, live Bedrock calls, real drafted output
against a real prospect (a sample run against Erewhon's newly announced Orange County
location is included in the repo). The full production design — five specialized agents,
a deterministic pipeline, deployment on Bedrock AgentCore Runtime, a human-approval
dashboard, and memory that learns from every rejection — is fully specified in
[`SPEC.md`](https://github.com/mel418/modo-matcha-sales-scout/blob/main/SPEC.md) in the
repo, alongside the reasoning for that architecture and a cost model.

## About the project (Devpost "Project Story" field)

### Inspiration

This is my mom's actual business. Mōdō Matcha has booked twelve brand partners — Meta, Adobe,
Benefit Cosmetics, Princess Polly, SEGA — in under a year of operating, and the honest number
behind that track record is that the majority of it is inbound: word of mouth, referrals,
agencies who already know the brand. There's no real outbound motion today, not because it
wouldn't work, but because a one-person shop running sales, production, and delivery has never
had a spare hour to build one. That's exactly the shape of problem this hackathon asked for —
routine, repetitive, and only valuable in its last five percent, the judgment call of whether
a lead is worth pursuing.

### What it does

Given nothing but a prompt to go find work, the agent searches the live web for a real company
with a genuine Los Angeles or Orange County event signal — a store opening, a funding round, a
product launch — and refuses to proceed without a real, verifiable source URL. A second pass
scores that company's fit against Mōdō Matcha's actual business rules (service lines, real
lead-time constraints, past case studies, the client roster) and drafts a first-touch email that
names the specific signal and cites the one case study that matches the prospect's segment. It
found and pitched Erewhon's newly announced Orange County location and MOTHER Denim's Beverly
Hills flagship opening, both with real, clickable sources — not invented leads.

### How we built it

The agent runs on the Strands Agents SDK against Amazon Bedrock (Claude, via inference
profiles), with Tavily as the live search tool. It's two agents, not one: a research agent that
holds the search tool and writes up findings in plain text, then a second, tool-free agent that
turns those findings into a validated Pydantic object — company, signal, score, reasons, and the
drafted email. That split exists because Strands' structured-output mode and live tool use
fight each other in a single call; separating "go find things" from "now structure what you
found" turned out to be both the fix and, honestly, the more honest architecture anyway.

### Challenges we ran into

The plan going in was five specialized agents (Scout, Researcher, Scorer, Writer, Critic)
chained by a deterministic pipeline and deployed on Bedrock AgentCore Runtime with a DynamoDB
lead store, AgentCore Memory, and a human-approval dashboard — that's still the full design,
written up in `SPEC.md`. The actual build window was a few hours, which meant descoping hard to
the two-agent core loop that proves the hardest part of the idea (can an LLM genuinely find,
verify, and pitch a real prospect end to end) without the deployment scaffolding around it.

The best bug of the project: a `.env` loading order issue meant the agent's very first real run
had no search API key at all — and it refused to invent a company rather than fail silently.
That's not a failure, it's the anti-hallucination behavior working exactly as designed, just
surfaced earlier and more honestly than planned.

### Accomplishments that we're proud of

Every output shown in this submission is real: live search results, live Bedrock calls, real
companies, real source URLs a judge can click and verify. Nothing was mocked to make the demo
look better than the code actually performs. And the pitch itself got more honest over the
course of building it — the first framing was "she's too busy to prospect"; the true story,
confirmed by the business owner, is that outbound has never existed at all. That's a better
and truer story, and it's the one this submission tells.

### What we learned

That Strands' `structured_output` and tool use don't reliably compose in a single call, and
that splitting research from structuring is the fix. That Bedrock model access and inference
profile availability are per-account and worth verifying with a one-line test call before
building anything on top of them. And that the most persuasive number in a pitch is sometimes
the one you almost didn't say out loud — that this business has never had an outbound channel
at all was a stronger hook than any efficiency claim would have been.

### What's next

The full system in `SPEC.md`: the five-agent deterministic pipeline, deployment on Bedrock
AgentCore Runtime behind a scheduled EventBridge trigger, DynamoDB for lead tracking and
dedupe, AgentCore Memory so the agent's scoring rubric improves from every real approval and
rejection, and a human-approval dashboard so no email ever sends without an explicit yes.

## Built with

Strands Agents SDK, Amazon Bedrock, Anthropic Claude, Tavily, Python, Pydantic

## Repo

https://github.com/mel418/modo-matcha-sales-scout

## AWS Builder ID

@melohdee

## Live demo link

https://mel418.github.io/modo-matcha-sales-scout/

A static showcase page — three real, unedited runs (95, 88, 45 out of 100, so the score
spread is visible) with source links and drafted emails. Hosted on GitHub Pages directly
from this repo's `docs/` folder — no backend, no live agent invocation, so there's
nothing for a visitor to cost you, and no sign-in wall since it's not behind any account.

## Testing instructions (Devpost "if applicable" field)

```
git clone https://github.com/mel418/modo-matcha-sales-scout.git
cd modo-matcha-sales-scout
python -m venv .venv && .venv\Scripts\Activate.ps1   # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`) with a free Tavily key (app.tavily.com) and AWS
credentials with Bedrock access in `us-east-1`. Then:

```
python -m src.scout.demo_agent
```

Takes 30-90 seconds and a few cents of Bedrock/Tavily usage per run. It will find a different
real company each time it's run — a saved real run is also included at
`tests/fixtures/sample_run_erewhon.txt` if you'd rather not run it live.

---

## Recording script for the demo video (≤5 min)

Don't write a script and read it — bullet points, talk naturally, one take.

1. **(30s) Problem.** Say the elevator pitch out loud. Lead with the honest framing: the
   majority of events today come from someone reaching out first — there's no real outbound
   motion. Show the Modo Matcha site for two seconds as proof this is a real business with a
   real gap.
2. **(30s) Who it's for.** The owner, one-person sales/production/delivery. Not a process that
   fell off her plate — a channel that's never existed because there was never a spare hour to
   build it.
3. **(2 min) Show it working.** Run `python -m src.scout.demo_agent` live, on screen.
   While it's searching (takes ~30-60s), talk over it: explain what it's doing right now
   (finding a real signal, verifying the URL). When the output prints, **click one of the
   source URLs it cites** — this is the single most convincing five seconds in the video,
   because it proves the agent didn't hallucinate the lead.
4. **(45s) Architecture.** Show `docs/architecture.svg`. Point at the green box: "this is
   what's running." Point at the gray dashed box: "this is the full system I designed for
   production — deployed on Bedrock AgentCore, with a dashboard so a human approves every
   send, memory so it learns from real rejections." Be upfront that the dashed part is
   designed, not deployed, and briefly say why (time, not doubt).
5. **(15s) Why it matters.** Tie back to the theme: this is exactly the kind of repetitive,
   judgment-heavy work the hackathon brief describes — and it only interrupts a human for
   the decision that's actually worth their attention.

If the live run is flaky when you hit record, fall back to showing
`tests/fixtures/sample_run_erewhon.txt` and say plainly on camera that it's a saved real
run — that's still honest, still real output, and removes API-flakiness risk from a
one-take recording.

## Submission checklist

- [x] Public repo — https://github.com/mel418/modo-matcha-sales-scout
- [x] MIT license — visible in file, confirm it shows in GitHub's About panel
- [x] README with quickstart + honest "built vs. designed" section
- [x] Architecture diagram — `docs/architecture.svg`
- [ ] Demo video ≤5 min, problem/who/why + live run
- [ ] Text description pasted into Devpost (above)
- [x] AWS Builder ID created and entered
- [ ] Submit
