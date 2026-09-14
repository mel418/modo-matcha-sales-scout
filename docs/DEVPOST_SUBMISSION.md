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
under a dozen people, doing sales, production, and delivery themselves. Outbound isn't a process
that fell off their plate — it's a channel that's never existed, because there was never a spare
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

This is a real business I'm close to. Mōdō Matcha has booked twelve brand partners in under
a year. Meta, Adobe, Benefit Cosmetics, Princess Polly, SEGA. That sounds great, but almost
all of it is inbound. People find them first. Word of mouth, referrals, agencies that already
know the brand. There's no real outbound today. Not because it wouldn't work. Because a one
person shop doing sales, production, and delivery has never had a spare hour to build one.
That's exactly the kind of problem this hackathon asked for. Routine. Repetitive. And the
only real value shows up in the last five percent, deciding if a lead is even worth chasing.

### What it does

Give it nothing but a prompt to go find work. The agent searches the live web for a real
company in LA or Orange County that just showed a signal, like a store opening, a funding
round, or a new product launch. It won't move forward without a real link backing it up.
Then a second pass scores how good a fit that company is, based on Mōdō Matcha's real rules:
service lines, how much lead time we need, past case studies, the client list. Then it writes
an email that names the exact signal and picks the one case study that actually matches. It
found and pitched Erewhon's new Orange County location and MOTHER Denim's Beverly Hills store
opening. Both real. Both with links you can click. Nothing made up.

### How we built it

It runs on the Strands Agents SDK, using Amazon Bedrock for the model, with Tavily doing the
live search. It's two agents, not one. The first agent has the search tool and just writes up
what it finds in plain text. The second agent has no tools. It takes that text and turns it
into a real structured object: company, signal, score, reasons, and the email. We split it
that way because Strands doesn't like using a tool and doing structured output in the same
call. They fight each other. Splitting them fixed the bug. And honestly, it's just a better
way to build it anyway.

### Challenges we ran into

The original plan was five agents. Scout, Researcher, Scorer, Writer, Critic. All chained
together, deployed on Bedrock AgentCore, with DynamoDB storing leads, AgentCore Memory, and a
dashboard where a human approves every email. That's still the full plan. It's written out in
`SPEC.md`. But we only had a few hours to actually build something. So we cut it down to two
agents. That's the hardest part of the idea anyway: can an AI actually find a real company,
check it's real, and write a good pitch. No deployment, no dashboard, just the core loop.

The best bug of the whole project: the `.env` file loaded in the wrong order, so the very
first real run had no search key at all. Instead of making up a fake company, the agent just
said it couldn't find one. That's not a bug. That's the agent doing exactly what it's supposed
to do. It just happened by accident before we meant it to.

### Accomplishments that we're proud of

Everything shown in this submission is real. Real search results, real Bedrock calls, real
companies, real links a judge can click and check themselves. Nothing was faked to make the
demo look better than the code actually is. The pitch also got more honest as we built it. At
first we said the business owner was too busy to do outreach. The real story, confirmed by
the owner, is that outreach never existed at all. That's a better story. And it's true. So
that's the one we're telling.

### What we learned

We learned that Strands structured output and tool use don't mix well in one call, and
splitting them fixes it. We learned that Bedrock model access depends on your account, so
it's worth testing with one simple call before building anything on top of it. And we learned
that the most convincing line in a pitch is sometimes the one you almost don't say. Saying
this business has never had an outbound channel at all was stronger than any efficiency pitch
could have been.

### What's next

The full system is in `SPEC.md`. Five agents working in a set order. Deployed on Bedrock
AgentCore Runtime. Triggered on a schedule with EventBridge. DynamoDB tracking every lead so
nothing gets contacted twice. AgentCore Memory so the scoring gets smarter every time the
owner approves or rejects something. And a dashboard so no email ever goes out without
someone actually saying yes.

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
   fell off their plate — a channel that's never existed because there was never a spare hour to
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
