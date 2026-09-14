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

sys.stdout.reconfigure(encoding="utf-8")  # Windows console defaults can't render em-dashes

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

Given the research notes, score fit (0-100) with concrete reasons tied to the
notes, pick the matching service line, choose exactly one proof point that
fits the prospect's segment, and draft a first-touch email under 150 words
that names the specific signal, cites that one proof point, respects the
lead-time rule, and never quotes a price. Use the exact source_url from the
notes — do not invent or alter it.
"""


class ProspectPitch(BaseModel):
    org_name: str
    domain: str | None = Field(None, description="Root domain, no scheme/www")
    signal_summary: str = Field(description="What happened, and when, in one or two sentences")
    source_url: HttpUrl = Field(description="A real URL that supports the signal")
    fit_score: int = Field(ge=0, le=100)
    fit_reasons: list[str] = Field(min_length=1)
    service_line: str = Field(description="brand_activation, corporate, or wedding")
    proof_point_used: str = Field(description="Which case study the email cites")
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
