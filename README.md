# Weekly Signal Digest

**A per-identity Monday morning briefing pipeline. Public signal sources, no CRM required.**

```
Monday 8am  →  [N sources]  →  [per-identity filter]  →  [Slack]  →  5-minute read
```

---

## The idea

Every Monday, every person who opted in wakes up to a per-identity
briefing of what changed in the world they care about over the week
before. Not a dump of everything that happened. Not a trending list
everyone sees. A **deterministic, per-person slice**, built from signal
sources they've said they care about, filtered through identity rules
they (or their ops team) wrote down once.

This is the architectural pattern behind the Monday-morning digests I've
built at work. That production version runs on proprietary CRM data and
stays inside an employer's private repo. This repo is the **pattern**,
rebuilt from scratch on public signal sources so you can read the
pipeline, run it yourself, and adapt it.

## What a digest looks like

```
▸ Sam Warren — week of Apr 19, 2026

GitHub Events (3 new)
  ✦ Anthropic/claude-code released v0.52.2 — new /recap command, MCP quiet-mode
  ✦ vercel/next.js shipped 16.3 canary with <Suspense> streaming
  ✦ tailwindlabs/tailwindcss opened RFC: color-mix() as a first-class primitive

Hacker News (2 new, filtered to "B2B ops")
  ✦ "Attribution is judgment, not a model" (52 comments)
  ✦ "Why every ops team rebuilds the same CRM sync" (38 comments)

RSS — Lenny's Newsletter (1 new)
  ✦ "How Stripe runs its weekly product review"

Read time: ~5 min. Reply in thread to correct a miss.
```

The interesting part isn't the digest UI. It's the pipeline that
produced it:

1. **Source adapters** fetch raw signals from public APIs and feeds.
2. **Normalizer** projects everything into a common `Signal` shape.
3. **Per-identity filter** matches signals to people based on their
   `interests` config — term lists, domain allowlists, tag filters.
4. **Ranker** orders what made it through: recency, engagement signals
   (HN points, GitHub stars delta), explicit priority overrides.
5. **Renderer** formats for the destination (Slack, stdout, markdown).
6. **Delivery** ships. Deterministic — same inputs produce the same
   output, always.
7. **Log** — every delivery records what fired, so when a person says
   "you missed X," you can see exactly why the filter didn't catch it.

Scheduled via GitHub Actions. State in SQLite. Credentials via env vars.
Everything observable end-to-end.

## What you get

```
weekly-signal-digest/
├── README.md                  this
├── LICENSE                    MIT
├── pyproject.toml
├── .github/workflows/
│   └── digest.yml             Monday 8am cron → run the pipeline
├── signal_digest/
│   ├── __init__.py
│   ├── core.py                Signal, Identity, pipeline run()
│   ├── filter.py              deterministic per-identity matching
│   ├── rank.py                recency + engagement-weighted ordering
│   ├── sources/
│   │   ├── rss.py             any RSS feed
│   │   ├── hacker_news.py     HN Algolia API
│   │   └── github_events.py   GitHub releases + issues
│   └── delivery/
│       ├── slack.py           webhook delivery
│       └── stdout.py          dev mode
├── fixtures/
│   ├── identities.yaml        2 imaginary people with interest configs
│   └── signals.jsonl          cached signals for tests + demo
└── tests/
```

## Quick start

```bash
git clone git@github.com:swsounds42/weekly-signal-digest.git
cd weekly-signal-digest
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run the demo pipeline against the bundled fixtures — prints to stdout
python3 -m signal_digest.cli --identities fixtures/identities.yaml --demo
```

To wire up your own identities:

```yaml
# identities.yaml
- name: Jane
  slack_channel: "#jane-digest"
  interests:
    terms: ["attribution", "revops", "b2b sales"]
    github_repos: ["anthropic/claude-code", "vercel/next.js"]
    rss_feeds: ["https://lennysnewsletter.com/feed"]
  max_items_per_section: 5
```

Then schedule it. The bundled GitHub Actions workflow runs every Monday
at 8am UTC; fork it and edit `cron:` to whatever fits.

## Design choices worth knowing

- **Deterministic.** Same inputs produce the same output. Stochastic
  "AI-enhanced personalization" is explicitly out of scope for v1.
  When someone says "you missed X," you should be able to trace
  *exactly* why — either the signal wasn't in the source data, or it
  didn't match the filter, or it got crowded out by higher-ranked
  items. No "the model decided."
- **Public sources only.** RSS, HN, GitHub — things anyone can see. The
  real production version at work wired in CRM signals (deal stage
  changes, rep activity, customer product usage) but those are
  company-specific. The pattern is the same; swap the sources.
- **Rank by scarcity, not volume.** One release from a repo you follow
  beats ten articles on a topic you don't actually care about. The
  ranker weights recency × engagement × explicit-priority. Tune or
  replace.
- **Per-identity config is static YAML.** Not a database, not a UI, not
  an LLM auto-tuning the interests. One file per person, live-editable,
  version-controlled. When someone's interests shift, they edit the
  file.
- **Delivery is a plugin.** Slack ships. Stdout ships. Email and
  Markdown-to-GitHub-issue are ~20 lines each to add.

## What this is *not*

- **Not a newsletter tool.** Substack or Beehiiv are better at
  newsletter mechanics. This is a pipeline for *personal/team briefings
  derived from source-of-truth data*, not broadcast content.
- **Not an inbox.** No thread management, no read-receipts, no
  archiving. Fire and forget; corrections happen in Slack threads.
- **Not a CRM-driven sales digest.** The production pattern this is
  derived from *does* do that. This repo deliberately doesn't — CRM
  wiring carries proprietary taxonomies that belong to whoever owns
  them.

## Why this is useful to see

Most "weekly digest" projects stop at: *wire up a cron, dump some
entries into Slack*. That part is the easy 10%. The interesting 90% is
everything around it — the per-identity filter, the deterministic
ranker, the correction log, the observability. This repo shows that
pattern end-to-end, small enough to read in an afternoon.

If you'd use this literally, clone it. If you'd adapt it to your own
CRM-driven digest use case, read the `filter.py` and `rank.py` modules
— that's where the interesting work is.

## License

MIT. See `LICENSE`.

## See also

- [samwarren.io/projects/target-account-news-agent](https://samwarren.io/projects/target-account-news-agent) — the case study on the production system this pattern comes from
- [cascade-attribution](https://github.com/swsounds42/cascade-attribution) — sister framework repo, rules-based classification for revenue attribution
