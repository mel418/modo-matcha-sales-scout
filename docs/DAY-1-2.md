# Days 1–2 — Foundation

A step-by-step bootcamp for the first two days of the Modo Matcha Sales Scout build.
Written for someone who has used AWS a little but hasn't wired a real system together yet.

**Every task has four parts:** why it exists, what it actually *is* in plain terms, the commands,
and how you know it worked. Don't skip the verify steps — half of AWS debugging is discovering on
day 7 that something on day 1 silently didn't take.

**Your machine, already checked:**

| | |
|---|---|
| Python | 3.12.7 (Anaconda) |
| git | 2.47.1 ✓ |
| winget | v1.29.290 ✓ |
| AWS CLI | 2.27.49 → **2.36.36 available** |
| AWS creds | configured, `us-east-1`, account `385122037268` |
| Repo | `C:\Users\melod\modo-matcha-sales-scout` — has `SPEC.md`, **not yet a git repo** |

---

# Mental model: what AWS actually is

Before any commands. If you only read one section, read this one.

**AWS is a warehouse of rented computers, and about 200 different ways to rent them.** That's it.
Everything else is vocabulary. The reason it feels overwhelming is that Amazon gives every rental
arrangement its own brand name, so a thing that would be one sentence gets four acronyms.

Here is the entire vocabulary you need for this project:

| Name | Caveman version |
|---|---|
| **Region** (`us-east-1`) | Which building your stuff physically lives in. Northern Virginia. Your things can only talk to your other things cheaply and easily if they're in the same building. **Keep everything in `us-east-1`.** Mixing regions is the #1 beginner time-sink — you create a thing in one building and then spend an hour wondering why the other building can't see it. |
| **IAM** | The bouncer. Decides who can do what. Nothing in AWS happens without IAM saying yes. |
| **IAM user** | A person's badge. Has a password and secret keys. **You** are an IAM user (`cloud-learning-user`). |
| **IAM role** | A costume a *machine* puts on to borrow permissions temporarily. Your Lambda doesn't have a badge — it wears a costume that says "I'm allowed to read DynamoDB." Roles are how machines get permissions without you leaving secret keys lying around. |
| **Access keys** | Your badge's magnetic strip. Two strings sitting in a plaintext file at `C:\Users\melod\.aws\credentials`. Anyone who copies them **is** you. Never commit them. Never paste them anywhere. |
| **Bedrock** | Rented brain. You send text, you get text back, you pay per word. This is where Claude lives. |
| **DynamoDB** | A dictionary/hash table that you rent and that survives forever. You put things in by key, you get them out by key. Not a real relational database — no joins, no `SELECT * WHERE anything you feel like`. You must decide your access patterns up front. (We did — see SPEC §7.) |
| **Lambda** | A function that only exists while it's running. No server to maintain. You hand AWS a Python function; it runs it when poked and then evaporates. Max 15 minutes per run. |
| **EventBridge Scheduler** | A rented alarm clock. "Poke this thing every day at 6am." |
| **Container / Docker image** | A zip file of an entire tiny computer — your code plus the OS plus every library, frozen. You hand AWS the zip; AWS unfreezes it and runs it. Solves "works on my machine." |
| **ECR** | Amazon's storage locker for those zip files. |
| **CodeBuild** | A rented build machine. It makes the zip file for you *in the cloud*, so you don't need Docker installed locally. **This is why you don't need Docker on Windows.** |
| **AgentCore Runtime** | A managed home for AI agents specifically. It runs your container, keeps sessions alive for hours, handles scaling. Think "Lambda, but designed for agents that need to think for ten minutes." |
| **AgentCore Memory** | A managed place for an agent to remember things between runs, with semantic search built in. |
| **SES** | A rented mail truck. Sends email on your behalf. |
| **App Runner** | Rented web hosting. You give it a container, it gives you back an `https://` URL. No load balancers, no networking to configure. |
| **CloudFormation** | A recipe file. Instead of clicking 40 buttons in the console, you write a YAML file describing what you want and AWS builds it. Also lets you delete everything in one command, which matters when you're on a budget. |

**One more concept that trips everyone up — inference profiles.**

You'd expect to call a model by name: `anthropic.claude-opus-5`. But you'll use
`us.anthropic.claude-opus-5`, with a `us.` on the front. That prefix means "run this in any US
region that has capacity, I don't care which." It exists because demand for the good models is
spiky, and letting AWS route your request across several regions means you get served instead of
throttled. **Use the `us.` prefix everywhere.** The bare ID often just errors.

---

# DAY 1 — Plumbing, and making sure it can't bankrupt you

Goal by tonight: every external dependency proven working, and a hard ceiling on spending.
**You will write almost no project code today.** That's correct and intentional. Today is about
discovering blockers while there are still eleven days left instead of two.

---

## 1.1 — Budget alarm (do this FIRST, before anything else)

### Why

You have $50 in credits. AWS's default behavior when you run out of credits is **to keep going and
charge your card**. There is no built-in stop. A runaway loop calling Opus 5 can spend real money
overnight, and "I was asleep" is not a refund category.

This takes six minutes and it is the highest-value six minutes of the whole project.

### What it actually is

A budget is a **tripwire, not a wall.** Important distinction: AWS Budgets will *email you* when
spending crosses a line. It will **not** stop anything. There is no switch anywhere in AWS that
says "turn off if it costs more than $50." The wall doesn't exist; you're building a smoke alarm,
not a sprinkler.

That's why the alarm needs to fire *early* — at $20, not at $50 — so you have room to react.

### How

Easiest path is the console, because the budget JSON is fiddly and this is a one-time thing:

1. Go to **https://console.aws.amazon.com/billing/home#/budgets**
2. **Create budget** → **Customize (advanced)** → **Cost budget**
3. Period **Monthly**, Budget amount **$50**
4. Add **three** alert thresholds — not one:
   - **40%** ($20) — "pay attention"
   - **70%** ($35) — "change something today"
   - **90%** ($45) — "stop and reassess"
5. Email: `melodygatan@gmail.com`
6. Create

Three thresholds instead of one because a single alarm at 90% tells you about a fire you can no
longer put out.

### Verify

```bash
aws budgets describe-budgets --account-id 385122037268 --query "Budgets[].{Name:BudgetName,Limit:BudgetLimit.Amount}" --output table
```

You should see your budget listed. Also **check your email** and confirm any subscription
notification — an unconfirmed alert address is a smoke alarm with the battery out.

> ⚠️ **Billing data lags 8–24 hours.** The alarm is a safety net, not a live dashboard. Don't rely
> on it to catch a runaway loop in real time — that's what `MAX_LEADS_PER_RUN` is for.

---

## 1.2 — Git repository, license, and `.gitignore`

### Why

Two hackathon rules depend on this: the repo must be public, and the MIT license must be visible
**in the GitHub About section** — not just as a `LICENSE` file. Doing it now means it can't be
forgotten at 11pm on day 12.

The `.gitignore` matters more than it looks. Your AWS secret keys live in a file on this machine,
and `.env` will hold your Tavily key. **Committing a secret to a public repo is not recoverable by
deleting it** — bots scrape GitHub commits within seconds of a push, and the key stays in git
history forever. You'd have to rotate the key.

### What it actually is

Git tracks changes. `.gitignore` is a list of "pretend these files don't exist." GitHub's About
section reads the `LICENSE` file automatically **only if** it's a recognized license text in the
repo root with no modifications — so paste the standard MIT text exactly, changing only the year
and name.

### How

```bash
cd C:\Users\melod\modo-matcha-sales-scout
git init
git branch -M main
```

Create `.gitignore`:

```gitignore
.env
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
.aws/
*.pem
bedrock_agentcore.yaml
.DS_Store
```

> `bedrock_agentcore.yaml` is ignored because `agentcore configure` writes account-specific ARNs
> into it. Commit `bedrock_agentcore.yaml.example` instead, later.

Create `LICENSE` with the standard MIT text, `Copyright (c) 2026 <your name>`.

Then on GitHub: create a **public** repo named `modo-matcha-sales-scout`, and after your first push,
go to the repo page → gear icon next to **About** → **License: MIT** should auto-populate. If it
doesn't, your LICENSE text was modified — paste it fresh.

```bash
git add .
git commit -m "Initial commit: spec, license, gitignore"
git remote add origin https://github.com/<you>/modo-matcha-sales-scout.git
git push -u origin main
```

### Verify

- `git status` shows a clean tree
- The GitHub About panel says **MIT** ✓
- **Critical:** `git ls-files | Select-String -Pattern "env|credential"` returns **nothing**

---

## 1.3 — Python environment

### Why

Two reasons, and the second is the one that bites people.

First, isolation: this project's libraries shouldn't collide with everything else Anaconda has
installed.

Second — and this is the one that matters on day 5 — **`requirements.txt` is what CodeBuild installs
into your container.** If you develop against whatever happens to be in your Anaconda base
environment, you will build a container missing half your dependencies and won't find out until the
deploy fails. A clean venv forces `requirements.txt` to be honest.

### What it actually is

A virtual environment is a folder with its own copy of Python and its own `site-packages`.
"Activating" it just puts that folder first on your PATH so `python` means *that* Python. Nothing
magic.

You're on Anaconda, which has its own environment system (`conda`). Either works — but use plain
`venv` here, because `requirements.txt` + pip is what the AgentCore container build expects, and
mixing conda and pip is a classic source of "works locally, breaks in the container."

### How

```powershell
cd C:\Users\melod\modo-matcha-sales-scout
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> If PowerShell blocks the activate script with an execution-policy error, run
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once and try again.

Your prompt should now start with `(.venv)`. **It must say that in every terminal where you run
project commands** — a new terminal starts deactivated, and forgetting is the most common cause of
"but I installed that already."

Create `requirements.txt`:

```
strands-agents
strands-agents-tools
bedrock-agentcore
bedrock-agentcore-starter-toolkit
boto3
pydantic
pydantic-settings
pyyaml
python-dotenv
fastapi
uvicorn
jinja2
pytest
```

```bash
pip install -r requirements.txt
```

### Verify

```bash
python -c "import strands, bedrock_agentcore, boto3, pydantic; print('all imports ok')"
```

If that prints, your environment is real. If it errors on `strands`, check your prompt says
`(.venv)`.

---

## 1.4 — Upgrade the AWS CLI

### Why

Your CLI is 2.27.49. The `bedrock-agentcore` and `bedrock-agentcore-control` command groups don't
exist in it — I confirmed this by running them; they error with "invalid choice." Since AgentCore is
the deployment target for the whole project, this is a hard blocker, and it's better discovered on
day 1 than day 5.

### What it actually is

The AWS CLI is a program that turns your typed commands into HTTPS requests to AWS. New AWS services
need a new CLI version because the command definitions ship *inside* the CLI. Old CLI literally
doesn't know the service exists.

### How

winget already sees the upgrade waiting:

```powershell
winget upgrade --id Amazon.AWSCLI --exact
```

Accept the UAC prompt (it's an MSI installer). **Then close and reopen your terminal** — Windows
caches the PATH, and the old binary will keep answering until you do.

### Verify

```bash
aws --version
aws bedrock-agentcore-control list-agent-runtimes --region us-east-1
```

First should show 2.36.x. Second should return `{"agentRuntimes": []}` — an **empty list is
success**. You haven't deployed anything yet; what matters is that the command *exists* now instead
of erroring with "invalid choice."

---

## 1.5 — Bedrock hello world (the single most important check today)

### Why

You've confirmed the model *profiles exist* in your account. You have **not** confirmed you can
actually invoke one. Those are different things — model access is a separate per-account setting,
and on some accounts you have to request it explicitly.

If this doesn't work, nothing else in the project works, so find out now.

### What it actually is

"Model access" is Bedrock's way of making you acknowledge each provider's terms before you can call
their models. Newer accounts often have Anthropic models enabled by default; older ones need a click
in the console under **Bedrock → Model access**. One call settles it.

This costs roughly **one twentieth of a cent.** Don't worry about it.

### How

Create `scripts/hello_bedrock.py`:

```python
"""Smallest possible proof that we can call Claude through Strands on Bedrock."""
from strands import Agent
from strands.models import BedrockModel

for model_id in ["us.anthropic.claude-sonnet-5", "us.anthropic.claude-opus-5"]:
    print(f"\n--- {model_id} ---")
    try:
        agent = Agent(
            model=BedrockModel(model_id=model_id, region_name="us-east-1"),
            system_prompt="Reply in exactly five words.",
        )
        print(agent("Say hello to Modo Matcha."))
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")
```

```bash
python scripts/hello_bedrock.py
```

### Verify

Both models should reply. **If you get `AccessDeniedException`:** go to
**https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess**, enable the Anthropic
models, wait a minute, retry.

**If you get `ValidationException` about the model id:** you dropped the `us.` prefix.

> 🧠 **What just happened, conceptually:** you created a `BedrockModel` (a configured connection to
> a rented brain), wrapped it in an `Agent` (Strands' loop that can call tools and keep
> conversation state), and called it like a function. That two-line pattern is the whole SDK. The
> other four agents in this project are the same thing with different prompts and different tools.

---

## 1.6 — Tavily API key

### Why

Tavily is how the Scout sees the world. Without it the agent has no input.

### What it actually is

A search API built for LLMs. Regular search gives you a page of blue links you'd have to scrape;
Tavily returns already-extracted clean text. That's the difference between "write an HTML parser"
and "read the content" — worth a lot on a 12-day clock.

The free tier is 1,000 credits/month, which is plenty for this project.

### How

1. Sign up at **https://app.tavily.com** → copy the key (starts `tvly-`)
2. Create `.env` in the repo root:

```dotenv
TAVILY_API_KEY=tvly-your-key-here
AWS_REGION=us-east-1
DDB_TABLE=modo-scout-leads
SCORE_THRESHOLD=65
MAX_LEADS_PER_RUN=6
MAX_SENDS_PER_DAY=10
SES_FROM=melodygatan@gmail.com
SES_ALLOWLIST=melodygatan@gmail.com
```

3. Create `.env.example` — same keys, values blanked. **This one gets committed;** `.env` never does.

### Verify

```bash
python -c "import os,dotenv;dotenv.load_dotenv();from strands_tools.tavily import tavily_search;print('key loaded:', bool(os.getenv('TAVILY_API_KEY')))"
```

Then confirm `.env` is invisible to git:

```bash
git check-ignore -v .env
```

It should print a line naming `.gitignore`. **Silence means it is NOT ignored — stop and fix it.**

---

## 1.7 — Verify SES identities (start early; it has an email round-trip)

### Why

This is the only task today with latency outside your control. Verification means AWS emails each
address and waits for a click. Start it now so it's done by the time you need it on day 8.

### What it actually is

SES in **sandbox mode** means: you can only send email *to* addresses you've proven you control. It
exists so new accounts can't be used as spam cannons.

For this project, **that limitation is a feature.** Per SPEC §9, the agent drafts real emails to
real researched prospects and shows them in full — only delivery is routed to your own inbox. The
demo looks identical, and no stranger gets cold-emailed by a prototype.

### How

```bash
aws sesv2 create-email-identity --email-address melodygatan@gmail.com --region us-east-1
```

Add one more address if you want a realistic "prospect received it" shot in the demo video (a second
inbox of your own).

**Check that inbox and click the AWS verification link.**

### Verify

```bash
aws sesv2 get-email-identity --email-identity melodygatan@gmail.com --region us-east-1 --query "VerifiedForSendingStatus"
```

Must print `true`. If `false`, the link hasn't been clicked yet.

---

## 1.8 — Send Casey the five questions

### Why

It's the only task with a dependency you don't control at all, and the answers materially improve
the scoring rubric. Send it today; the rubric ships with defaults either way so nothing blocks.

### The five (SPEC §6)

1. Of the twelve brand partners, which came to you versus you going to them?
2. Typical guest count and rough price band for each of the three service lines?
3. **The last few enquiries you turned down — and why?** (Highest-value answer by far. These become
   the agent's seed memories.)
4. Who actually signs off — a brand manager, an office manager, or the agency's producer?
5. Which case study do you lead with, for which type of client?

---

## Day 1 end-of-day checklist

- [ ] Budget alarm live at 40/70/90%, email confirmed
- [ ] Git repo initialized, pushed, **public, MIT visible in About**
- [ ] `.env` confirmed git-ignored
- [ ] `.venv` active, all imports working
- [ ] AWS CLI 2.36.x, `bedrock-agentcore-control` command exists
- [ ] **Both Claude models replied** ← the one that matters
- [ ] Tavily key in `.env`
- [ ] SES identity `VerifiedForSendingStatus: true`
- [ ] Questions sent to Casey

**If the Bedrock call failed and you couldn't fix it, stop and solve that before day 2.** Everything
downstream assumes it works.

---

# DAY 2 — Teach the computer what Modo Matcha knows

Today is mostly typing, and almost all of it is knowledge rather than logic. By tonight the project
knows the business, and one real agent runs.

---

## Mental model: Pydantic and structured output

The concept the whole codebase rests on. Worth two minutes.

**The problem.** Language models emit text. You want data. The naive approach — "reply in JSON" then
`json.loads()` — fails constantly: the model wraps it in markdown fences, adds a friendly preamble,
invents a field, uses a string where you wanted a number. You end up writing retry loops and regex,
and it's still flaky.

**Pydantic** is a bouncer for data shapes. You describe what a valid object looks like, in Python:

```python
class FitScore(BaseModel):
    score: int = Field(ge=0, le=100)
    tier: Literal["hot", "warm", "cool", "disqualified"]
    reasons: list[str] = Field(min_length=1)
```

That's a contract: score is an integer 0–100, tier is exactly one of four strings, reasons is a
non-empty list. Anything else gets rejected at the door.

**Structured output** is where it gets good. `agent.structured_output(FitScore, prompt)` takes your
Pydantic class, converts it into a *tool definition*, and hands it to the model. The model doesn't
write JSON in prose — it **calls a function**, and function arguments are already structured. Strands
validates the result against your class and hands you a real `FitScore` object.

**Caveman version:** don't ask the model to write you a letter and then try to parse the letter. Hand
it a form with labeled boxes and make it fill in the boxes.

Practical consequences worth internalizing:

- **Your Pydantic models ARE your prompts.** A `Field(description=...)` is read by the model. Writing
  a good description is prompt engineering.
- **Making an invalid state unrepresentable beats asking nicely.** `size_band` has an explicit
  `"unknown"` option so the model has a legal way to not know. If it didn't, the model would guess —
  not from dishonesty, but because you gave it no valid alternative. This is the single most useful
  trick in the whole project.

---

## 2.1 — `src/scout/settings.py`

### Why

One place where all configuration lives. The alternative — `os.getenv()` scattered across fifteen
files — means a typo'd env var name fails silently at 6am inside a container you can't see into.

### What it actually is

`pydantic-settings` reads environment variables and `.env`, validates them against a class, and
**crashes immediately on startup** if something's missing or the wrong type. Failing loudly at
startup beats failing weirdly at 3am.

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    tavily_api_key: str
    aws_region: str = "us-east-1"
    ddb_table: str = "modo-scout-leads"

    score_threshold: int = 65
    max_leads_per_run: int = 6
    max_sends_per_day: int = 10

    ses_from: str
    ses_allowlist: str = ""

    model_scout: str = "us.anthropic.claude-sonnet-5"
    model_research: str = "us.anthropic.claude-sonnet-5"
    model_score: str = "us.anthropic.claude-opus-5"
    model_write: str = "us.anthropic.claude-opus-5"
    model_critic: str = "us.anthropic.claude-opus-5"

    config_dir: Path = REPO_ROOT / "config"

    @property
    def allowlist(self) -> list[str]:
        return [e.strip().lower() for e in self.ses_allowlist.split(",") if e.strip()]

settings = Settings()
```

> 💡 Model IDs live here, not hardcoded in the agents. When credits get tight on day 8, dropping a
> stage from Opus to Sonnet is a one-line change in `.env` — no code edit, no redeploy of logic.

### Verify

```bash
python -c "from src.scout.settings import settings; print(settings.model_score, settings.allowlist)"
```

---

## 2.2 — The four config YAMLs

### Why

Per SPEC §6, nothing about Modo Matcha is hardcoded in Python. Two payoffs: Casey's answers become a
YAML edit rather than a code change, and the "generalizes to any local service business" claim in
your pitch is demonstrably true rather than aspirational.

### What it actually is

YAML is a human-friendly way to write nested data. Indentation makes the structure — **spaces only,
never tabs**, which is the one way YAML bites beginners.

Write these four in `config/`. Content comes from `modomatchasummary.md`:

**`business.yaml`** — service area, lead times (branded cups 10 business days, branded cart 15,
therefore ≥3 weeks for branded), deposit 50% non-refundable, balance due 3 days prior, cancellation
terms, setup requirements (8'×8', dedicated circuit, elevator), dietary facts, no tastings, COI on
request.

**`proof_points.yaml`** — the three case studies, each tagged with the segments it suits:

```yaml
case_studies:
  benefit_love_wellness:
    title: "Benefit × Love Wellness — Valentine's influencer activation, West Hollywood"
    segments: [brand_activation, beauty, wellness, influencer]
    detail: "~90 influencers, two heated pilates classes, custom strawberry matcha
             developed through several rounds of ideation with the Benefit team."
    hook: "custom menu item designed with the brand team"

  grant_thornton:
    title: "Grant Thornton new-hire welcome, Downtown LA"
    segments: [corporate, professional_services, office, new_hire]
    detail: "High floor, skyline backdrop, every drink whisked to order as the line
             kept forming. No batching, no urns."
    hook: "hand-whisked to order even at volume"

  bel_air_bay_club:
    title: "Oceanfront wedding, Bel-Air Bay Club, Pacific Palisades"
    segments: [wedding, celebration, luxury]
    detail: "Bluff lawn, shared matcha pour during the vows, cups illustrated with the couple."
    hook: "a ceremony moment, not just a drink station"

testimonials:
  - {who: "Kristen", role: "Events Manager & Producer", org: "Princess Polly",
     quote_gist: "one of the most talked-about elements of their events"}
  - {who: "Samantha", role: "Office Manager", org: "SEGA",
     quote_gist: "hand-whisked for a team of 200, elevated"}

clients: [Meta, Adobe, Innisfree, Vuori, Morphe, Benefit Cosmetics, Love Wellness,
          Princess Polly, Bioderma, SEGA, Splits59, MZ Wallace, Three Ships Beauty,
          Naturepedic, Velocity Black, Compass]

credibility_line: "Twelve brand partners in under a year of operating."
```

> The `segments` tags are what let the Writer pick the *right* case study. A wedding story sent to an
> office manager is exactly the mistake the Critic exists to catch.

**`icp.yaml`** — the scoring rubric. Start with defaults; tune with Casey's answers:

```yaml
threshold: 65
weights:
  geography: 25        # LA/OC presence — the hard constraint
  signal_strength: 25  # dated, specific, recent event trigger
  segment_fit: 20      # beauty/wellness/fashion/tech offices/agencies
  size_fit: 15         # enough people to justify a cart
  timing: 15           # lead time actually workable

disqualifiers:
  - "No evidence of Los Angeles or Orange County presence"
  - "Event date inside the branded lead time with no unbranded option viable"
  - "Already contacted (handled in code by domain dedupe, not by the model)"

tier_bands: {hot: 80, warm: 65, cool: 45}
```

**`search_strategies.yaml`** — the three signal families from SPEC §5, as parameterized Tavily
queries with `topic`, `time_range`, and domain hints.

### Verify

```bash
python -c "import yaml,pathlib; [print(p.name, 'ok') for p in pathlib.Path('config').glob('*.yaml') if yaml.safe_load(p.read_text(encoding='utf-8')) is not None]"
```

All four should print `ok`. A YAML error here is almost always a tab character.

---

## 2.3 — `src/scout/models.py`

### Why

Every stage boundary in the pipeline is a Pydantic model. Writing them all first means each agent is
a pure function from one known shape to another — which is what makes them independently testable
against fixtures, which is what lets you develop without spending money.

### What

Transcribe all the models from SPEC §4: `Candidate`, `SourcedClaim`, `CompanyProfile`, `FitScore`,
`Draft`, `CritiqueResult`.

**Write the `Field(description=...)` text carefully.** The model reads those. This is the highest
prompt-engineering-leverage hour of the whole project.

```python
class SourcedClaim(BaseModel):
    """A factual claim with the URL that supports it.

    Wrapping claims this way makes fabrication structurally awkward: there is no
    way to represent a claim without a source, so the model must either find
    evidence or leave the field null.
    """
    value: str
    source_url: HttpUrl
```

### Verify

Write `tests/test_models.py` — construct one valid instance of each, and assert that an invalid one
raises:

```python
import pytest
from pydantic import ValidationError
from src.scout.models import FitScore

def test_score_must_be_in_range():
    with pytest.raises(ValidationError):
        FitScore(score=150, tier="hot", reasons=["x"])

def test_tier_must_be_known():
    with pytest.raises(ValidationError):
        FitScore(score=70, tier="lukewarm", reasons=["x"])
```

```bash
pytest tests/ -v
```

> 🧠 These tests cost five minutes and they're testing your *contracts*, not your logic. When an
> agent starts returning something odd on day 6, a green test here tells you the problem is the
> prompt, not the schema.

---

## 2.4 — First real agent: the Scout

### Why

End day 2 with something that actually does the job. This proves the three things the rest of the
project assumes: Strands can drive a tool, Tavily returns usable results for this specific niche,
and structured output holds.

### What it actually is

An agent is a loop. You give the model a question and a list of tools. It answers, or it calls a
tool; if it calls a tool, Strands runs the function, feeds the result back, and asks again. Repeat
until it stops calling tools. That loop is the entire idea behind "agent" — everything else is
prompt and plumbing.

`src/scout/agents/scout.py`:

```python
from strands import Agent
from strands.models import BedrockModel
from strands_tools.tavily import tavily_search
from ..settings import settings
from ..models import Candidate

SYSTEM = """You find businesses in Los Angeles and Orange County that have just done
something implying they will host an event soon.

Qualifying signals: a new retail store or pop-up opening; a funding round; a dated
product launch; an experiential agency running a local campaign; a company hiring an
events producer or announcing a large new-hire class.

Rules:
- Los Angeles or Orange County only. No LA/OC evidence means do not return it.
- Every candidate needs a real source_url you actually saw in search results.
- Prefer a dated, specific signal over a vague one.
- Six well-sourced candidates beat twenty guesses. Quality over volume.
- Do not invent companies. If a search returns nothing useful, return fewer."""

class CandidateList(BaseModel):
    candidates: list[Candidate]

def run_scout(query: str) -> list[Candidate]:
    agent = Agent(
        model=BedrockModel(model_id=settings.model_scout, region_name=settings.aws_region),
        tools=[tavily_search],
        system_prompt=SYSTEM,
    )
    return agent.structured_output(CandidateList, query).candidates
```

> **Why the `CandidateList` wrapper?** `structured_output` needs a single model class, not a bare
> `list[...]`. Wrapping a list in an object with one field is the standard workaround.

Smoke test it:

```python
# scripts/try_scout.py
from src.scout.agents.scout import run_scout

for c in run_scout("Brands that opened a new retail store or pop-up in Los Angeles "
                   "or Orange County in the last 14 days"):
    print(f"{c.org_name:35} {c.signal_type:18} {c.source_url}")
```

```bash
python scripts/try_scout.py
```

### Verify

Real company names, real signal types, **real URLs you can click**. Open two or three. If a URL
404s, the model invented it and the prompt needs a harder line about sourcing.

Expect this to cost about **$0.05–0.10** per run and take 30–60 seconds. It's doing several searches
and reading the results.

**Then immediately capture a fixture:**

```python
import json, pathlib
from src.scout.agents.scout import run_scout
out = run_scout("...")
pathlib.Path("tests/fixtures/scout_run_01.json").write_text(
    json.dumps([c.model_dump(mode="json") for c in out], indent=2), encoding="utf-8")
```

> 💰 **This is your cost-control strategy, not just a testing nicety.** From here on, develop against
> saved fixtures and hit the live API only when you're deliberately testing the live path. This is
> the difference between finishing inside $50 and not.

---

## Day 2 end-of-day checklist

- [ ] `settings.py` loads and prints real values
- [ ] Four YAMLs parse clean
- [ ] All six Pydantic models written, with real `description=` text
- [ ] `pytest tests/ -v` green
- [ ] **`try_scout.py` returns real LA/OC companies with clickable URLs** ← the one that matters
- [ ] At least one fixture saved to `tests/fixtures/`
- [ ] Committed and pushed

---

# What day 3 looks like

You'll have the hardest agent working. Days 3–4 are the same pattern four more times — Researcher,
Scorer, Writer, Critic — plus `store.py` (DynamoDB) and `pipeline.py` (the loop that chains them).

The day-4 milestone is `python scripts/run_local.py` producing real drafts for real leads on your own
machine, no AWS deployment involved. **That's the spine of the project.** Everything from day 5 on is
deployment and presentation — genuinely important for the hackathon score, but it's packaging around
a thing that already works.

---

# Glossary

| Term | Caveman version |
|---|---|
| **Agent** | A loop: model answers or calls a tool; if it calls a tool, run it, feed the result back, ask again. Repeat until it stops. |
| **Tool** | A Python function the model is allowed to call. It sees the name, the docstring, and the parameters — so the docstring *is* documentation for the model. |
| **System prompt** | Standing instructions. The job description, not the task. |
| **Structured output** | Hand the model a form with labeled boxes instead of asking for a letter you'd have to parse. |
| **Pydantic model** | A bouncer for data shapes. Invalid data doesn't get in. |
| **Fixture** | A saved real response, replayed later. Free, instant, identical every time. |
| **Deterministic pipeline** | Python decides the *order*; the models decide the *judgments*. |
| **Idempotent** | Running it twice does no more damage than running it once. Domain-keyed dedupe is what makes the agent idempotent — it's why it can't email the same company twice. |
| **ARN** | `arn:aws:service:region:account:thing/name` — a globally unique address for one AWS resource. Long, ugly, and the thing you'll paste most often. |
| **Sandbox (SES)** | Training wheels: you can only email addresses you've proven you own. |
| **Inference profile** | The `us.` prefix. "Run this in whichever US region has capacity." |
| **Cold start** | First request after idle is slow because the container has to wake up. |
| **Checkpoint** | Save progress after every unit of work, so a crash costs one lead instead of the whole run. |
