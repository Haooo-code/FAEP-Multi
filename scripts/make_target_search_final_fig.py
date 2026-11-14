#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 2026-11-15 目标触发式搜索最终回归图。"""

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

labels = [
    "正常高置信目标",
    "低检测率 0.60",
    "错误先验",
    "严格双机 #1",
    "严格双机 #2",
    "严格双机 #3",
    "假检测注入",
    "关闭目标搜索",
    "无目标兜底",
]
times = np.array([20, 22, 23, 41, 35, 29, 48, 74, 92])
colors = [
    "#1a73e8",
    "#1a73e8",
    "#1a73e8",
    "#185abc",
    "#185abc",
    "#185abc",
    "#e37400",
    "#b6bdc7",
    "#6b7280",
]

fig, ax = plt.subplots(figsize=(11.2, 6.2), dpi=160)
y = np.arange(len(labels))
bars = ax.barh(y, times, color=colors, height=0.62)

for bar, value in zip(bars, times):
    ax.text(
        value + 1.4,
        bar.get_y() + bar.get_height() / 2,
        f"{value}s",
        va="center",
        fontsize=10,
        color="#202124",
    )

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=10)
ax.invert_yaxis()
ax.set_xlim(0, 105)
ax.set_xlabel("从触发到三机 HALT 的 wall time（秒）", fontsize=10)
ax.grid(axis="x", color="#d9dde3", linewidth=0.8, alpha=0.8)
ax.set_axisbelow(True)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.tick_params(axis="y", length=0)

ax.set_title("office2 目标触发式探索最终回归", fontsize=15, pad=18, color="#202124")
fig.text(
    0.5,
    0.025,
    "严格双机三轮均通过交叉视角确认并三机停止；图中时间用于机制验证，不用于统计显著性结论。",
    ha="center",
    fontsize=9,
    color="#5f6368",
)
fig.tight_layout(rect=(0, 0.06, 1, 1))

out = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "figures",
    "fig_target_search_final_20261115.png",
)
fig.savefig(out, dpi=300, facecolor="white")
print("WROTE", out)
