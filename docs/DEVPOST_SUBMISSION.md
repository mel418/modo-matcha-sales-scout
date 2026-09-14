# Devpost submission — copy/paste draft

Fill in the brackets, paste into the Devpost form. Don't overthink wording under time
pressure — this is already honest and complete; polish is not worth spending minutes on.

---

## Project name

**Modo Matcha Sales Scout**

## Elevator pitch (one line, if the form asks)

An autonomous sales agent that finds real Los Angeles brands about to need an event,
verifies the signal, and drafts the outreach email — so a small catering business never
has to go looking for its next client.

## Track

Professional Agents

## Text description

**The problem.** Mōdō Matcha is a mobile matcha-bar catering company that's booked twelve
brand partners — Meta, Adobe, Benefit Cosmetics, Princess Polly, SEGA — in under a year.
The bottleneck isn't the pitch, it's finding out who needs one. Every week, someone has to
read LA business and beauty press, notice who just opened a store or launched a product,
judge whether they're a real fit, find the right contact, and write something specific
enough not to sound like the fifteenth vendor email that week. That's hours of repetitive
work whose only real value is the very last step — deciding whether it's worth sending.

**Who it's for.** Casey, and every operator like her: a founder running a service business
under a dozen people, doing sales, production, and delivery herself. Prospecting is the
first thing that falls off the list when the week gets busy — and its absence shows up
two months later as an empty calendar.

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

## Built with

Strands Agents SDK, Amazon Bedrock, Anthropic Claude, Tavily, Python, Pydantic

## Repo

https://github.com/mel418/modo-matcha-sales-scout

## AWS Builder ID

[fill in once created — profile.aws.amazon.com]

## Live demo link

[skip — not required; core loop is a local script for this submission]

---

## Recording script for the demo video (≤5 min)

Don't write a script and read it — bullet points, talk naturally, one take.

1. **(30s) Problem.** Say the elevator pitch out loud. Show `modomatchasummary.md` or the
   Modo Matcha site for two seconds as proof this is a real business with a real gap.
2. **(30s) Who it's for.** Casey, one-person sales/production/delivery. The repetitive
   90% vs. the judgment-call 10%.
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
- [ ] AWS Builder ID created and entered
- [ ] Submit
