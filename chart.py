#!/usr/bin/env python3
"""One chart: SO questions per quarter 2008-2026, hand-sketch style (black on white)."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with open("stackoverflow_raw.json") as f:
    RAW = json.load(f)
q = RAW["quarterly"]

with plt.xkcd(scale=0.6, length=120, randomness=1.2):
    fig, ax = plt.subplots(figsize=(10.8, 8.2), dpi=120)
    xs = list(range(len(q)))
    ys = [r["questions"] for r in q]
    labels = [r["quarter"] for r in q]

    ax.plot(xs, ys, color="black", linewidth=2.4)
    ax.fill_between(xs, ys, color="black", alpha=0.06)

    # annotate peak
    pk = max(range(len(q)), key=lambda i: ys[i])
    ax.annotate(f"peak: {labels[pk]}\n~{ys[pk]//3000}k questions/month",
                xy=(pk, ys[pk]), xytext=(pk + 6, ys[pk] * 0.97),
                fontsize=13, arrowprops=dict(arrowstyle="->", color="black"))

    # annotate ChatGPT launch (2022Q4)
    cg = next(i for i, r in enumerate(q) if r["quarter"] == "2022Q4")
    ax.axvline(cg, color="black", linestyle="--", linewidth=1.2)
    ax.annotate("ChatGPT\nNov 2022", xy=(cg, ys[pk] * 0.55),
                xytext=(cg - 14, ys[pk] * 0.62), fontsize=13,
                arrowprops=dict(arrowstyle="->", color="black"))

    # annotate last point
    ax.annotate(f"{labels[-1]}: {ys[-1]:,}\nbelow the 2008\nlaunch quarter",
                xy=(len(q) - 1, ys[-1]), xytext=(len(q) - 20, ys[pk] * 0.28),
                fontsize=13, arrowprops=dict(arrowstyle="->", color="black"))

    tick_idx = [i for i, r in enumerate(q) if r["quarter"].endswith("Q1")][::2]
    ax.set_xticks(tick_idx)
    ax.set_xticklabels([labels[i][:4] for i in tick_idx], fontsize=12)
    ax.set_yticks([0, 150_000, 300_000, 450_000, 600_000])
    ax.set_yticklabels(["0", "150k", "300k", "450k", "600k"], fontsize=12)
    ax.set_title("Stack Overflow: questions per quarter, 2008-2026",
                 fontsize=17, pad=18)
    ax.set_xlabel("Source: Stack Exchange API, pulled 2026-06-12 · "
                  "godi.ai", fontsize=10)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig("chart_questions_per_quarter.png", facecolor="white")
print("saved chart_questions_per_quarter.png")
