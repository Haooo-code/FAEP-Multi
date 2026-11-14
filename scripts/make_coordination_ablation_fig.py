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
labels = ["L1 独立", "L2 协调无分区", "L3 扇区协同"]
colors = ["#aeb6c2", "#e37400", "#1a73e8"]


def get_value(scene, level, key):
    row = next(item for item in rows if item["scene"] == scene and item["level"] == level)
    return float(row[key])


fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.3), dpi=160)
for ax, value_key, std_key, title, ylabel in (
    (axes[0], "mission_time_mean_s", "mission_time_std_s", "每轮三机平均飞行时间", "秒"),
    (axes[1], "wall_mean_s", "wall_std_s", "每轮总时长 wall", "秒"),
):
    x = np.arange(len(scenes))
    width = 0.23
    for index, (level, label, color) in enumerate(zip(levels, labels, colors)):
        means = [get_value(scene, level, value_key) for scene in scenes]
        stds = [get_value(scene, level, std_key) for scene in scenes]
        bars = ax.bar(
            x + (index - 1) * width,
            means,
            width,
            yerr=stds,
            capsize=3,
            color=color,
            label=label,
        )
        for bar_, value in zip(bars, means):
            ax.text(
                bar_.get_x() + bar_.get_width() / 2,
                value + 5,
                f"{value:.0f}",
                ha="center",
                fontsize=8,
            )
    ax.set_xticks(x)
    ax.set_xticklabels(["office", "office2", "office3"])
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    ax.set_ylim(0, 330)

axes[0].legend(frameon=False, fontsize=8, loc="upper left", ncol=3)
fig.suptitle("三级协同消融：增加协调器不必然变快，空间分区才形成主要收益", fontsize=14, y=0.985)
fig.text(
    0.5,
    0.018,
    "轮数 office/office2/office3 = 5/5/3；误差线为轮间标准差，旧版冻结数据统一复算。",
    ha="center",
    fontsize=9,
    color="#5f6368",
)
fig.tight_layout(rect=(0, 0.055, 1, 0.94))
fig.savefig(OUT_PATH, dpi=300, facecolor="white")
print("WROTE", OUT_PATH)
