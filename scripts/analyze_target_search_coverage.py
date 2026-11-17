#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总 office3 跨场景目标搜索与发现时覆盖率。"""

import csv
import json
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np


FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if os.path.exists(FONT_PATH):
    plt.rcParams["font.family"] = ["sans-serif"]
    plt.rcParams["font.sans-serif"] = [
        "Noto Sans CJK SC",
        "Droid Sans Fallback",
        "DejaVu Sans",
    ]
    if not any(getattr(item, "fname", "") == FONT_PATH for item in fm.fontManager.ttflist):
        fm.fontManager.ttflist.append(
            fm.FontEntry(
                fname=FONT_PATH,
                name="Noto Sans CJK SC",
                style="normal",
                variant="normal",
                weight="normal",
                stretch="normal",
                size="scalable",
            )
        )
plt.rcParams["axes.unicode_minus"] = False

LOG_DIR = os.environ.get("TARGET_COVERAGE_LOG_DIR", "/mnt/d/WSL/target_search_office3_20261115")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_CSV = os.path.join(ROOT, "data", "target_search_office3_coverage_20261115.csv")
OUT_PNG = os.path.join(ROOT, "docs", "figures", "fig_target_search_office3_coverage_20261115.png")

CONFIGS = [
    ("office3_normal", "正常目标并停止", True),
    ("office3_wrong_prior", "错误先验并停止", True),
    ("office3_no_target", "无目标兜底", False),
    ("office3_target_continue", "确认后继续", False),
]


def read_summary(name):
    values = {}
    with open(os.path.join(LOG_DIR, f"{name}_summary.txt"), encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                values[key] = value
    return values


def read_coverage(name):
    with open(os.path.join(LOG_DIR, f"{name}_coverage.json"), encoding="utf-8") as handle:
        return json.load(handle)


def clean_ansi(value):
    return re.sub(r"\x1b\[[0-9;]*m", "", value or "")


rows = []
for name, label, stopped in CONFIGS:
    summary = read_summary(name)
    coverage = read_coverage(name)
    status = coverage.get("status_coverage") or {}
    halt = coverage.get("halt_coverage") or {}
    status_time = float(status.get("time_from_start_s", 0))
    halt_time = float(halt.get("time_from_start_s", status_time))
    wall_time = float(summary.get("wall_s", 0))
    recorder_offset = max(0.0, halt_time - wall_time)
    status_time_from_wall = max(0.0, status_time - recorder_offset)
    extra_time_from_wall = max(0.0, halt_time - status_time)
    status_coverage = float(status.get("union_coverage_pct", 0))
    halt_coverage = float(halt.get("union_coverage_pct", 0))
    rows.append(
        {
            "scenario": name,
            "label": label,
            "wall_s": summary.get("wall_s", ""),
            "result": summary.get("result", ""),
            "stopped_on_confirm": int(stopped),
            "status": status.get("state", ""),
            "status_time_s": f"{status_time:.2f}",
            "halt_time_s": f"{halt_time:.2f}",
            "extra_time_s": f"{extra_time_from_wall:.2f}",
            "status_time_from_wall_s": f"{status_time_from_wall:.2f}",
            "halt_time_from_wall_s": f"{wall_time:.2f}",
            "grid_m": coverage.get("grid_m", ""),
            "radius_m": coverage.get("radius_m", ""),
            "free_cells": status.get("free_cells", halt.get("free_cells", "")),
            "status_union_cells": status.get("union_cells", ""),
            "halt_union_cells": halt.get("union_cells", ""),
            "status_coverage_pct": f"{status_coverage:.2f}",
            "halt_coverage_pct": f"{halt_coverage:.2f}",
            "extra_coverage_pp": f"{max(0.0, halt_coverage - status_coverage):.2f}",
            "multi_pct_of_union_at_status": status.get("multi_pct_of_union", ""),
            "confirm_or_not_found": clean_ansi(summary.get("confirm", "") or summary.get("not_found", "")),
        }
    )

with open(OUT_CSV, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

labels = [row["label"] for row in rows]
status_cov = np.array([float(row["status_coverage_pct"]) for row in rows])
halt_cov = np.array([float(row["halt_coverage_pct"]) for row in rows])
status_time = np.array([float(row["status_time_from_wall_s"]) for row in rows])
extra_time = np.array([float(row["extra_time_s"]) for row in rows])

fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.4), dpi=160)
x = np.arange(len(rows))
width = 0.34

ax = axes[0]
ax.bar(x - width / 2, status_cov, width, color="#1a73e8", label="目标状态时")
ax.bar(x + width / 2, halt_cov, width, color="#9aa0a6", label="三机 HALT 时")
for index in x:
    ax.text(index - width / 2, status_cov[index] + 1.5, f"{status_cov[index]:.1f}", ha="center", fontsize=8)
    ax.text(index + width / 2, halt_cov[index] + 1.5, f"{halt_cov[index]:.1f}", ha="center", fontsize=8)
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=12, ha="right")
ax.set_ylim(0, 100)
ax.set_ylabel("轨迹 1m 邻域并集覆盖率 (%)")
ax.set_title("目标状态与最终 HALT 的覆盖率", fontsize=11)
ax.grid(axis="y", alpha=0.25)
ax.legend(frameon=False, loc="upper left")

ax = axes[1]
ax.bar(x, status_time, color="#1a73e8", width=0.58, label="到目标状态")
ax.bar(x, extra_time, bottom=status_time, color="#e37400", width=0.58, label="确认后额外探索")
for index in x:
    total = status_time[index] + extra_time[index]
    ax.text(index, total + 2.0, f"{total:.1f}s", ha="center", fontsize=8)
    if extra_time[index] > 1:
        ax.text(
            index,
            status_time[index] + extra_time[index] / 2,
            f"+{extra_time[index]:.1f}s",
            ha="center",
            va="center",
            color="white",
            fontsize=8,
        )
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=12, ha="right")
ax.set_ylabel("从统一任务触发起算的时间 (s)")
ax.set_title("目标状态时间与确认后的额外探索", fontsize=11)
ax.grid(axis="y", alpha=0.25)
ax.legend(frameon=False, loc="upper left")

fig.suptitle("office3 目标搜索：跨场景验证与发现时覆盖率", fontsize=14, y=0.985)
fig.text(
    0.5,
    0.015,
    "覆盖率按1m网格上轨迹1m邻域近似；图内时间均从统一任务触发计时，与表8一致。",
    ha="center",
    fontsize=9,
    color="#5f6368",
)
fig.tight_layout(rect=(0, 0.055, 1, 0.94))
fig.savefig(OUT_PNG, dpi=300, facecolor="white")
print("WROTE", OUT_CSV)
print("WROTE", OUT_PNG)
