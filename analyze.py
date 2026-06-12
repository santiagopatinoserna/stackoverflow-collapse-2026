#!/usr/bin/env python3
"""
Analyze Stack Overflow question-volume data pulled by fetch.py.

Computes:
  1. Peak quarter/level, current level, total decline
  2. Decay decomposition: pre-ChatGPT (2014 peak -> 2022Q3) vs post (2023Q1 -> last)
     -> compound monthly decay rate each period + acceleration factor
  3. Post-ChatGPT volume half-life (months)
  4. "Time machine" equivalence: which early year matches today's volume
  5. Tag asymmetry table: 2025 volume as % of 2019 (or 2022) baseline
  6. AI-era corpus gap: langchain lifetime corpus vs pandas
  7. Answers-per-question supply ratio over time

Outputs: stackoverflow_analysis.csv + stackoverflow_analysis.json + stdout report
"""
import json
import csv
import math

with open("stackoverflow_raw.json") as f:
    RAW = json.load(f)

q = RAW["quarterly"]          # [{quarter, start, questions}]
mo = RAW["monthly"]           # [{month, questions}] 2025-01..2026-05
tags = RAW["tags"]            # [{tag, 2022, 2024, 2025}]
answers = RAW["answers"]      # [{year, answers|None}]

report = {"methodology": {
    "source": "Stack Exchange API /2.3/questions filter=total, anonymous quota",
    "pulled_at": RAW["meta"]["pulled_at_utc"],
    "normalization": "raw counts; decay rates are compound monthly rates fitted between period endpoints",
    "caveats": [
        "Counts are questions surviving today (deleted/removed questions not included) — historical figures are slightly undercounted vs what was asked at the time; this biases AGAINST the collapse narrative, not for it.",
        "Cohort-relative tag analysis: a tag's decline measures public Q&A activity, not the technology's real-world usage.",
        "What this does NOT measure: question quality, answer accuracy, lurker traffic (pageviews), private/Teams usage, LLM answer quality.",
        "June 2026 is partial and excluded; last full month = May 2026.",
    ],
}}

# ---- 1. Peak vs now ----
peak = max(q, key=lambda r: r["questions"])
last_q = q[-1]
last_m = mo[-1]
first_full_2009 = [r for r in q if r["start"].startswith("2009")]
total_decline = 1 - last_q["questions"] / peak["questions"]

print("=" * 70)
print(f"PEAK:    {peak['quarter']}  {peak['questions']:,} questions/quarter "
      f"(~{peak['questions']//3:,}/month)")
print(f"LATEST FULL QUARTER: {last_q['quarter']}  {last_q['questions']:,} "
      f"(~{last_q['questions']//3:,}/month)")
print(f"LATEST MONTH: {last_m['month']}  {last_m['questions']:,}")
print(f"TOTAL DECLINE FROM PEAK: {total_decline*100:.1f}%")
report["peak"] = peak
report["latest_quarter"] = last_q
report["latest_month"] = last_m
report["total_decline_pct"] = round(total_decline * 100, 1)

# ---- 2. Decay decomposition ----
def cmr(v0, v1, months):
    """compound monthly rate between two levels"""
    return (v1 / v0) ** (1 / months) - 1

def q_idx(label):
    return next(i for i, r in enumerate(q) if r["quarter"] == label)

# pre-ChatGPT: peak quarter -> 2022Q3 (last full quarter before ChatGPT 2022-11-30)
pre0, pre1 = peak, q[q_idx("2022Q3")]
pre_months = (q_idx("2022Q3") - q_idx(peak["quarter"])) * 3
pre_rate = cmr(pre0["questions"], pre1["questions"], pre_months)

# post-ChatGPT: 2023Q1 -> last full quarter
post0 = q[q_idx("2023Q1")]
post_months = (len(q) - 1 - q_idx("2023Q1")) * 3
post_rate = cmr(post0["questions"], last_q["questions"], post_months)

accel = post_rate / pre_rate if pre_rate != 0 else float("inf")
print(f"\nPRE-CHATGPT DECAY  ({peak['quarter']}->2022Q3, {pre_months} months): "
      f"{pre_rate*100:.2f}%/month compound")
print(f"POST-CHATGPT DECAY (2023Q1->{last_q['quarter']}, {post_months} months): "
      f"{post_rate*100:.2f}%/month compound")
print(f"ACCELERATION FACTOR: {accel:.1f}x")
pre_total = 1 - pre1["questions"] / pre0["questions"]
print(f"Already lost BEFORE ChatGPT: {pre_total*100:.1f}% "
      f"({pre0['questions']:,} -> {pre1['questions']:,}/quarter)")
report["decay"] = {
    "pre_chatgpt_monthly_pct": round(pre_rate * 100, 2),
    "post_chatgpt_monthly_pct": round(post_rate * 100, 2),
    "acceleration_factor": round(accel, 1),
    "decline_before_chatgpt_pct": round(pre_total * 100, 1),
    "pre_window": f"{peak['quarter']}->2022Q3",
    "post_window": f"2023Q1->{last_q['quarter']}",
}

# ---- 3. Half-life post-ChatGPT ----
half_life = math.log(0.5) / math.log(1 + post_rate)
print(f"\nPOST-CHATGPT HALF-LIFE: volume halves every {half_life:.1f} months")
report["post_chatgpt_half_life_months"] = round(half_life, 1)

# ---- 4. Time machine ----
older = [r for r in q if r["questions"] <= last_q["questions"]]
print(f"\nTIME MACHINE: quarters at or below today's volume: "
      f"{[r['quarter'] for r in older if not r['quarter'].startswith('202')]}")
report["time_machine_quarters"] = [r["quarter"] for r in older]

# ---- 5. Tag asymmetry ----
print("\nTAG ASYMMETRY (2025 as % of 2022):")
tag_rows = []
for t in tags:
    base = t.get("2022", 0)
    now = t.get("2025", 0)
    pct = (now / base * 100) if base else None
    tag_rows.append({"tag": t["tag"], "y2022": base,
                     "y2024": t.get("2024"), "y2025": now,
                     "retention_2025_vs_2022_pct": round(pct, 1) if pct is not None else None})
    if pct is not None:
        print(f"  {t['tag']:<12} 2022: {base:>7,}  2025: {now:>6,}  retention: {pct:.1f}%")
    else:
        print(f"  {t['tag']}: no 2022 base")
tag_rows.sort(key=lambda r: (r["retention_2025_vs_2022_pct"] is None,
                             r["retention_2025_vs_2022_pct"]))
report["tags"] = tag_rows

# ---- 6. AI-era corpus gap ----
lc = next((t for t in tags if t["tag"] == "langchain"), None)
pd_ = next((t for t in tags if t["tag"] == "pandas"), None)
if lc and pd_:
    yrs = [k for k in lc if k != "tag"]
    lc_total = sum(lc[k] or 0 for k in yrs)
    pd_total = sum(pd_[k] or 0 for k in yrs)
    print(f"\nCORPUS GAP (sampled years {sorted(yrs)}):")
    print(f"  langchain: {lc_total:,} questions | pandas: {pd_total:,} "
          f"-> pandas/langchain = {pd_total/max(lc_total,1):.0f}x")
    report["corpus_gap"] = {"langchain_sampled": lc_total, "pandas_sampled": pd_total,
                            "ratio": round(pd_total / max(lc_total, 1), 1)}

# ---- 7. Answers supply ----
print("\nANSWERS PER YEAR:")
for a in answers:
    val = f"{a['answers']:,}" if a["answers"] is not None else "UNAVAILABLE (API timeout)"
    print(f"  {a['year']}: {val}")
report["answers_yearly"] = answers

# ---- save ----
with open("stackoverflow_analysis.json", "w") as f:
    json.dump(report, f, indent=2)
with open("stackoverflow_analysis.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["quarter", "questions"])
    for r in q:
        w.writerow([r["quarter"], r["questions"]])
    w.writerow([])
    w.writerow(["month", "questions"])
    for r in mo:
        w.writerow([r["month"], r["questions"]])
    w.writerow([])
    w.writerow(["tag", "2022", "2024", "2025", "retention_2025_vs_2022_pct"])
    for r in tag_rows:
        w.writerow([r["tag"], r["y2022"], r["y2024"], r["y2025"],
                    r["retention_2025_vs_2022_pct"]])
print("\nSaved stackoverflow_analysis.json + stackoverflow_analysis.csv")
