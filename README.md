# Stack Overflow Collapse — 2026 Data

18 years of Stack Overflow question volumes, pulled from the public Stack Exchange API on **2026-06-12**, plus the analysis behind the post/article:

- **May 2026: 2,435 questions** — the entire site. At the Q1 2014 peak (583,310/quarter) that volume arrived every ~9 hours.
- **Q1 2026 (10,199) is the lowest quarter in site history** — below the 2008 beta launch quarter (17,776).
- **The decline pre-dates ChatGPT by 8 years**: -43.9% from the 2014 peak to autumn 2022 (-0.56%/month compound).
- **ChatGPT multiplied the decay rate 15.4x**: -8.70%/month compound since Q1 2023 → volume halves every 7.6 months.
- **Tag asymmetry**: pandas kept 2.5% of its 2022 volume; rust kept 16.7%. AI absorbed exactly the questions it was trained on.
- **Corpus gap**: LangGraph = 56.9M PyPI downloads/month and 147 lifetime Stack Overflow questions. pandas = 288,928 questions (~2,000x more).

## Reproduce

```bash
python3 fetch.py     # ~120 anonymous API calls, checkpointed (resume-safe)
python3 analyze.py   # decay rates, half-life, tag table -> CSV/JSON
python3 chart.py     # the quarterly chart
```

No API key needed (anonymous quota: 300 req/day/IP). Numbers reproduce within normal deletion drift — counts are questions *surviving today*, which undercounts old quarters and makes the decline conservative.

## Files

| File | What |
|---|---|
| `fetch.py` | Pull quarterly/monthly/tag/answer counts from the Stack Exchange API |
| `analyze.py` | Decay decomposition, half-life, tag retention, corpus gap |
| `chart.py` | Questions-per-quarter chart (2008–2026) |
| `stackoverflow_raw.json` | Raw API counts |
| `stackoverflow_analysis.json` / `.csv` | Computed results + methodology + caveats |
| `supplement_ai_era_tags.json` | langchain / langgraph / pandas lifetime pulls |
| `supplement_pypi_agent_frameworks.json` | PyPI last-month downloads (pypistats.org) |
| `chart_questions_per_quarter.png` | The chart |

## Caveats (what this does NOT measure)

Deleted questions (survivor counts only), read traffic, private LLM chats (unobservable), tag confounders (rust culture ≠ only LLM coverage), Q&A that moved to GitHub/Discord. Q3 2008 is a partial quarter — which makes "below the launch quarter" conservative.

Found an error? Open an issue — I'd rather correct it than defend it.

— Santiago Patino Serna · santiagopatinoserna@godi.ai
