#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成三级协同消融图。"""

import csv
import os

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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "data", "coordination_level_ablation_results_20261115.csv")
OUT_PATH = os.path.join(ROOT, "docs", "figures", "fig_coordination_ladder_20261115.png")

rows = []
with open(CSV_PATH, encoding="utf-8") as handle:
    rows.extend(csv.DictReader(handle))

scenes = ["office", "office2", "office3"]
levels = ["L1", "L2", "L3"]
labels = ["L1 三机独立", "L2 协调无分区", "L3 扇区协同"]
colors = ["#aeb6c2", "#e37400", "#1a73e8"]


def get_value(scene, level, key):
    row = next(item for item in rows if item["scene"] == scene and item["level"] == level)
    return float(row[key])


fig, axes = plt.subplots(1, 2, figsize=(16, 9), dpi=120)
for ax, value_key, std_key, title, ylabel in (
    (axes[0], "mission_time_mean_s", "mission_time_std_s", "每轮平均单机飞行时间", "飞行时间（秒）"),
    (axes[1], "wall_mean_s", "wall_std_s", "每轮总耗时 wall", "wall 总耗时（秒）"),
):
    x = np.arange(len(scenes))
    width = 0.22
    for index, (level, label, color) in enumerate(zip(levels, labels, colors)):
        means = [get_value(scene, level, value_key) for scene in scenes]
        stds = [get_value(scene, level, std_key) for scene in scenes]
        bars = ax.bar(
            x + (index - 1) * width,
            means,
            width,
            yerr=stds,
            capsize=4,
            color=color,
            label=label,
        )
        for bar_, value in zip(bars, means):
            ax.text(
                bar_.get_x() + bar_.get_width() / 2,
                value - 10,
                f"{value:.0f}",
                ha="center",
                va="top",
                fontsize=11,
                fontweight="bold",
                color="#243447" if level == "L1" else "white",
            )
    ax.set_xticks(x)
    ax.set_xticklabels(["office", "office2", "office3"])
    ax.tick_params(axis="both", labelsize=13)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=16, pad=12)
    ax.grid(axis="y", alpha=0.28)
    ax.set_ylim(0, 370)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

handles, legend_labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles,
    legend_labels,
    frameon=False,
    fontsize=14,
    ncol=3,
    loc="upper center",
    bbox_to_anchor=(0.5, 0.865),
)
fig.suptitle(
    "三级协同消融：只加协调器不会更快，真正收益来自空间分区",
    fontsize=20,
    y=0.985,
)
fig.text(
    0.5,
    0.925,
    "L2 相对 L1：平均单机飞行时间增加 21.1%–29.3%",
    ha="center",
    va="center",
    fontsize=16,
    color="white",
    bbox={"boxstyle": "round,pad=0.45", "facecolor": "#10243D", "edgecolor": "none"},
)
fig.text(
    0.5,
    0.025,
    "轮数 office/office2/office3 = 5/5/3；误差线为轮间标准差；"
    "wall = 统一触发到三机全部完成或停止的实际耗时。",
    ha="center",
    fontsize=12,
    color="#5f6368",
)
fig.subplots_adjust(left=0.085, right=0.985, top=0.75, bottom=0.13, wspace=0.16)
fig.savefig(OUT_PATH, dpi=300, facecolor="white")
print("WROTE", OUT_PATH)
