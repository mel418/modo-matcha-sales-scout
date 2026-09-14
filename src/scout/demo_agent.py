"""
Modo Matcha Sales Scout — hackathon submission core loop.

This is the single-agent version of the pipeline designed in SPEC.md. The full
spec calls for five specialized agents (Scout, Researcher, Scorer, Writer,
Critic) chained by a deterministic Python pipeline, deployed on Bedrock
AgentCore Runtime, with a human-approval dashboard and SES sending.

Given the build window for this submission, that architecture is the target
design, not what's running here. What's running here is the same judgment
compressed into one Strands agent with one tool: it searches the live web for
a real LA/OC company showing a buying signal, researches it, scores it against
Modo Matcha's actual ICP, and drafts a first-touch email — end to end, for
real, against real search results and a real Bedrock model.

See README.md "What's built vs. what's designed" for the honest breakdown.
"""

from __future__ import annotations

import sys
import warnings
import webbrowser
from html import escape
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults can't render em-dashes
warnings.filterwarnings("ignore", category=DeprecationWarning)  # Strands attributes this to the call site, not its own module

from dotenv import load_dotenv

load_dotenv()  # must run before importing strands_tools.tavily, which reads TAVILY_API_KEY at import time

from pydantic import BaseModel, Field, HttpUrl
from strands import Agent
from strands.models import BedrockModel
from strands_tools.tavily import tavily_search

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
REGION = "us-east-1"

# Condensed from modomatchasummary.md — the real business facts, inlined
# because the full config/*.yaml layer from SPEC.md didn't get built in time.
BUSINESS_CONTEXT = """
MODO MATCHA — business facts to use in scoring and drafting:

- Mobile, on-site organic matcha bar and catering. Serves Los Angeles and
  Orange County (broader SoCal for a travel fee). Every drink hand-whisked
  to order in front of guests, never batched, from a fully branded cart,
  served by "matcharistas."
- Three service lines: brand_activation, corporate, wedding.
- Twelve brand partners in under a year: Meta, Adobe, Innisfree, Vuori,
  Morphe, Benefit Cosmetics, Love Wellness, Princess Polly, Bioderma, SEGA,
  Splits59, MZ Wallace, Three Ships Beauty, Naturepedic, Velocity Black,
  Compass.
- Proof points to cite (pick ONE that matches the prospect's segment):
    * Benefit x Love Wellness — Valentine's influencer activation, West
      Hollywood. ~90 influencers, custom "Strawberry Matcha" developed with
      the brand team. Best for: beauty, wellness, influencer/brand
      activations.
    * Grant Thornton — new-hire welcome, Downtown LA. Every drink whisked to
      order even as the line kept forming, no batching. Best for: corporate,
      office teams, professional services.
    * Bel-Air Bay Club — oceanfront wedding, Pacific Palisades. Shared matcha
      pour during the vows. Best for: weddings, milestone celebrations.
- Lead times: branded cups need 10 business days, a fully branded cart needs
  15 business days — so a fully branded activation needs booking at least
  3 weeks out. If the signal implies an event sooner than that, the email
  should NOT promise full branding — offer the unbranded experience instead.
- Never quote a price. Pricing is per-event after date, guest count, venue
  are known. The email's call to action is to share those three things.
- Deposit is 50%, non-refundable. (Don't put this in a cold email — it's
  booking-stage detail, not outreach detail.)
"""

RESEARCH_PROMPT = f"""You are a B2B sales research agent for Modo Matcha, a
mobile matcha catering company. Your job:

1. Use tavily_search to find ONE real company or organization that plausibly
   has a Los Angeles or Orange County presence and has recently done
   something that implies they will host an event soon — a new retail store
   or pop-up opening, a funding round, a dated product launch, an
   experiential agency's local campaign, or a company hiring an events
   producer / announcing a large new-hire class.
2. Confirm real LA/OC presence and gather the actual signal with a real,
   working source URL — do not invent a company or a URL.

{BUSINESS_CONTEXT}

Write up what you found in plain text: company name, domain, the specific
signal and when it happened, the real source URL, and anything else relevant
to whether Modo Matcha should reach out. If you cannot find a real,
verifiable company, say so honestly instead of inventing one.
"""

STRUCTURE_PROMPT = f"""You turn sales research notes into a structured pitch
for Modo Matcha, a mobile matcha catering company.

{BUSINESS_CONTEXT}

Watch for a specific trap: if the notes mention the prospect already has an
in-house café, bar, or beverage program — including one that already serves
matcha — do NOT treat that as generic positive brand alignment. A prospect
who already serves matcha day-to-day has an obvious objection ready:
"why would we pay you, we already have this?" Modo Matcha is not a beverage
vendor, it's a live, hand-whisked-to-order EVENT experience — an entertainment
moment for a one-off activation, not a fixed daily menu item. That distinction
is the entire fit argument when an existing offering is in play. If the notes
don't give you a clear, specific angle for that distinction, lower the fit
score and say so plainly in fit_reasons instead of papering over it. If you do
proceed, the email must explicitly name the existing offering and explain why
this is different — a launch-day or activation moment, not daily service —
rather than mentioning it as a pleasant detail.

Given the research notes, score fit (0-100) with concrete reasons tied to the
notes, pick the matching service line, choose exactly one proof point that
fits the prospect's segment, and draft a first-touch email under 150 words
that names the specific signal, cites that one proof point, respects the
lead-time rule, and never quotes a price. Use the exact source_url from the
notes — do not invent or alter it. For proof_point_used, give ONLY the short
case-study name (e.g. "Grant Thornton") — never the full case-study
description.
"""


class ProspectPitch(BaseModel):
    org_name: str
    domain: str | None = Field(None, description="Root domain, no scheme/www")
    signal_summary: str = Field(description="What happened, and when, in one or two sentences")
    source_url: HttpUrl = Field(description="A real URL that supports the signal")
    fit_score: int = Field(ge=0, le=100)
    fit_reasons: list[str] = Field(min_length=1)
    service_line: str = Field(description="brand_activation, corporate, or wedding")
    proof_point_used: str = Field(
        description="Short name only, e.g. 'Benefit x Love Wellness', 'Grant Thornton', "
        "or 'Bel-Air Bay Club' — never the full case-study description"
    )
    email_subject: str = Field(max_length=80)
    email_body: str


def run_one() -> ProspectPitch:
    researcher = Agent(
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        tools=[tavily_search],
        system_prompt=RESEARCH_PROMPT,
    )
    notes = researcher("Find one real prospect right now and report your findings.")

    writer = Agent(
        model=BedrockModel(model_id=MODEL_ID, region_name=REGION),
        system_prompt=STRUCTURE_PROMPT,
    )
    return writer.structured_output(ProspectPitch, str(notes))


REPORT_PATH = Path(__file__).resolve().parents[2] / "reports" / "latest_run.html"

REPORT_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Modo Matcha — Verified Pitch</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,700;1,9..144,500&family=Libre+Franklin:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {{
    --bg:#F3F0E3; --surface:#EAE5D2; --ink:#1C2116; --ink-soft:#52573F;
    --line:#D2CAAC; --accent:#62762F; --accent-strong:#4A5C22; --accent-2:#A8823C;
    --font-display:'Fraunces',serif; --font-body:'Libre Franklin',sans-serif; --font-mono:'IBM Plex Mono',monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#12150D; --surface:#1A1F13; --ink:#ECE7D5; --ink-soft:#AEAC90;
             --line:#333A22; --accent:#9DB35A; --accent-strong:#B4C874; --accent-2:#D2AD68; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font-family:var(--font-body);
          padding:clamp(2rem,5vw,4rem); }}
  .wrap {{ max-width:52rem; margin:0 auto; }}
  .eyebrow {{ font-family:var(--font-mono); font-size:0.78rem; letter-spacing:0.14em;
              text-transform:uppercase; color:var(--accent-2); margin-bottom:1rem; }}
  h1 {{ font-family:var(--font-display); font-weight:600; font-size:clamp(1.8rem,4vw,2.6rem);
        margin:0 0 0.3rem; text-wrap:balance; }}
  .domain {{ font-family:var(--font-mono); font-size:0.95rem; color:var(--ink-soft);
             margin-bottom:2rem; }}
  .card {{ background:var(--surface); border:1px solid var(--line); border-radius:6px;
           padding:1.6rem 1.9rem; margin-bottom:1.4rem; }}
  .row {{ display:flex; justify-content:space-between; gap:1.5rem; padding:0.55rem 0;
          border-bottom:1px solid var(--line); }}
  .row:last-child {{ border-bottom:none; }}
  .k {{ font-family:var(--font-mono); font-size:0.72rem; letter-spacing:0.08em;
        text-transform:uppercase; color:var(--ink-soft); white-space:nowrap; padding-top:0.15rem; }}
  .v {{ text-align:right; font-size:0.98rem; }}
  .v a {{ color:var(--accent-strong); word-break:break-all; }}
  .score {{ font-family:var(--font-display); font-size:2rem; color:var(--accent-strong); }}
  .reasons {{ margin:0; padding-left:1.2rem; }}
  .reasons li {{ margin-bottom:0.4rem; line-height:1.4; }}
  .email-card {{ background:var(--surface); border:1px solid var(--line); border-radius:6px;
                 padding:1.8rem 2rem; }}
  .cite-line {{ font-family:var(--font-mono); font-size:0.72rem; letter-spacing:0.05em;
                text-transform:uppercase; color:var(--ink-soft); margin-bottom:0.6rem;
                white-space:normal; overflow-wrap:break-word; }}
  .email-subject {{ font-family:var(--font-display); font-weight:600; font-size:1.2rem;
                     margin-bottom:1rem; }}
  .email-body {{ line-height:1.6; white-space:pre-wrap; }}
</style></head>
<body><div class="wrap">
  <div class="eyebrow">Verified Prospect &middot; Live Search + Bedrock</div>
  <h1>{org_name}</h1>
  <div class="domain">{domain}</div>

  <div class="card">
    <div class="row"><span class="k">Signal</span><span class="v">{signal_summary}</span></div>
    <div class="row"><span class="k">Source</span><span class="v"><a href="{source_url}" target="_blank" rel="noopener">{source_url}</a></span></div>
    <div class="row"><span class="k">Service line</span><span class="v">{service_line}</span></div>
    <div class="row"><span class="k">Fit score</span><span class="v score">{fit_score}/100</span></div>
  </div>

  <div class="card">
    <div class="k" style="margin-bottom:0.6rem;">Why it's a fit</div>
    <ul class="reasons">{reasons_html}</ul>
  </div>

  <div class="email-card">
    <div class="cite-line">Drafted outreach &middot; cites {proof_point}</div>
    <div class="email-subject">{email_subject}</div>
    <div class="email-body">{email_body}</div>
  </div>
</div></body></html>
"""


def render_report(pitch: ProspectPitch) -> Path:
    """Render a single-result report card — not the multi-lead approval dashboard
    from SPEC.md, just a clean view of one run's output instead of terminal scroll."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    source_url = escape(str(pitch.source_url))
    html = REPORT_TEMPLATE.format(
        org_name=escape(pitch.org_name),
        domain=escape(pitch.domain or "domain unknown"),
        signal_summary=escape(pitch.signal_summary),
        source_url=source_url,
        service_line=escape(pitch.service_line),
        fit_score=pitch.fit_score,
        reasons_html="".join(f"<li>{escape(r)}</li>" for r in pitch.fit_reasons),
        proof_point=escape(pitch.proof_point_used),
        email_subject=escape(pitch.email_subject),
        email_body=escape(pitch.email_body).replace("\n", "<br>"),
    )
    REPORT_PATH.write_text(html, encoding="utf-8")
    return REPORT_PATH


def _print_pitch(pitch: ProspectPitch) -> None:
    print("\n" + "=" * 72)
    print(f"PROSPECT:      {pitch.org_name}  ({pitch.domain or 'domain unknown'})")
    print(f"SIGNAL:        {pitch.signal_summary}")
    print(f"SOURCE:        {pitch.source_url}")
    print(f"FIT SCORE:     {pitch.fit_score}/100  (service line: {pitch.service_line})")
    print("FIT REASONS:")
    for r in pitch.fit_reasons:
        print(f"  - {r}")
    print(f"PROOF POINT:   {pitch.proof_point_used}")
    print("-" * 72)
    print(f"SUBJECT: {pitch.email_subject}")
    print()
    print(pitch.email_body)
    print("=" * 72 + "\n")


if __name__ == "__main__":
    result = run_one()
    _print_pitch(result)
    report_path = render_report(result)
    print(f"Report saved to {report_path}")
    webbrowser.open(report_path.as_uri())
