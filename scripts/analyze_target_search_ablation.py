#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总目标触发式搜索组件消融，并生成 CSV 与配图。"""

import csv
import os
import re
import statistics as st

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


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

LOG_DIR = os.environ.get("ABLATION_LOG_DIR", "/mnt/d/WSL/target_search_ablation_20261115")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_CSV = os.path.join(ROOT, "data", "target_search_ablation_results_20261115.csv")
OUT_PNG = os.path.join(ROOT, "docs", "figures", "fig_target_search_ablation_20261115.png")

TIME_RE = re.compile(r"\[(?:WARN|INFO|ERROR)\] \[([0-9.]+)\]")
CONFIRM_RE = re.compile(
    r"\[target\] CONFIRMED source=(drone\d+) confidence=([0-9.]+) "
    r"position=\(([-0-9.]+), ([-0-9.]+), ([-0-9.]+)\) reason=([^\x1b]+)"
)

CONFIGS = [
    {
        "config": "full",
        "label": "完整方案",
        "condition": "先验开 / 3帧 / 换人开 / 确认停止",
        "target": "(1,3)",
        "logs": ["ablation_full_pilot", "ablation_full_1", "ablation_full_2"],
    },
    {
        "config": "prior_on_east",
        "label": "目标先验开",
        "condition": "目标(5,5)，先验(5,5)",
        "target": "(5,5)",
        "logs": [
            "ablation_prior_on_east_1",
            "ablation_prior_on_east_2",
            "ablation_prior_on_east_3",
        ],
    },
    {
        "config": "prior_off_east",
        "label": "目标先验关",
        "condition": "目标(5,5)，不使用先验",
        "target": "(5,5)",
        "logs": [
            "ablation_prior_off_east_1",
            "ablation_prior_off_east_2",
            "ablation_prior_off_east_3",
        ],
    },
    {
        "config": "handoff_on",
        "label": "无进展换人开",
        "condition": "高阈值1.0，换人时限10s",
        "target": "(1,3)",
        "logs": [
            "ablation_with_handoff_strict_pilot",
            "ablation_with_handoff_strict_1",
            "ablation_with_handoff_strict_2",
        ],
    },
    {
        "config": "handoff_off",
        "label": "无进展换人关",
        "condition": "高阈值1.0，换人时限999s",
        "target": "(1,3)",
        "logs": [
            "ablation_no_handoff_pilot",
            "ablation_no_handoff_1",
            "ablation_no_handoff_2",
        ],
    },
    {
        "config": "confirm_3frame",
        "label": "3帧确认",
        "condition": "多帧门槛开启",
        "target": "(1,3)",
        "logs": ["ablation_full_pilot", "ablation_full_1", "ablation_full_2"],
    },
    {
        "config": "confirm_1frame",
        "label": "单帧确认",
        "condition": "多帧门槛关闭",
        "target": "(1,3)",
        "logs": [
            "ablation_single_frame_pilot_new",
            "ablation_single_frame_1",
            "ablation_single_frame_2",
        ],
    },
    {
        "config": "stop_on",
        "label": "确认后停止",
        "condition": "stop_on_confirm=true",
        "target": "(1,3)",
        "logs": ["ablation_full_pilot", "ablation_full_1", "ablation_full_2"],
    },
    {
        "config": "stop_off",
        "label": "确认后继续",
        "condition": "stop_on_confirm=false",
        "target": "(1,3)",
        "logs": [
            "ablation_no_stop_pilot",
            "ablation_no_stop_1",
            "ablation_no_stop_2",
        ],
    },
]


def read_summary(log_name):
    path = os.path.join(LOG_DIR, f"{log_name}_summary.txt")
    values = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    return values


def parse_log(log_name):
    path = os.path.join(LOG_DIR, f"{log_name}.log")
    confirm_time = None
    halt_time = None
    confirm_source = ""
    confirm_position = ""
    confirm_reason = ""
    prioritize_count = 0
    global_fallback_count = 0
    verifier_switch_count = 0
    detection_count = 0
    verification_state_count = 0
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if "[TARGET] prioritize" in line:
                prioritize_count += 1
            if "no frontier in priority radius" in line:
                global_fallback_count += 1
            if "verifier no progress" in line:
                verifier_switch_count += 1
            if "[target_perception_sim] drone" in line and "candidate confidence" in line:
                detection_count += 1
            if "[target] state=VERIFYING" in line:
                verification_state_count += 1
            if "[target] CONFIRMED" in line:
                time_match = TIME_RE.search(line)
                detail = CONFIRM_RE.search(line)
                if time_match:
                    confirm_time = float(time_match.group(1))
                if detail:
                    confirm_source = detail.group(1)
                    confirm_position = (
                        f"({detail.group(3)}, {detail.group(4)}, {detail.group(5)})"
                    )
                    confirm_reason = detail.group(6).strip()
            if "HALT received" in line and halt_time is None:
                time_match = TIME_RE.search(line)
                if time_match:
                    halt_time = float(time_match.group(1))
    delay = ""
    if confirm_time is not None and halt_time is not None:
        delay = f"{halt_time - confirm_time:.2f}"
    return {
        "confirm_source": confirm_source,
        "confirm_position": confirm_position,
        "confirm_reason": confirm_reason,
        "confirm_to_halt_s": delay,
        "prioritize_count": prioritize_count,
        "global_fallback_count": global_fallback_count,
        "verifier_switch_count": verifier_switch_count,
        "detection_count": detection_count,
        "verification_state_count": verification_state_count,
    }


rows = []
for config in CONFIGS:
    for run, log_name in enumerate(config["logs"], start=1):
        summary = read_summary(log_name)
        parsed = parse_log(log_name)
        rows.append(
            {
                "config": config["config"],
                "label": config["label"],
                "condition": config["condition"],
                "target": config["target"],
                "run": run,
                "log_name": log_name,
                "wall_s": summary.get("wall_s", ""),
                "result": summary.get("result", ""),
                "halt_count": summary.get("halt_count", ""),
                "confirm_source": parsed["confirm_source"],
                "confirm_position": parsed["confirm_position"],
                "confirm_reason": parsed["confirm_reason"],
                "confirm_to_halt_s": parsed["confirm_to_halt_s"],
                "prioritize_count": parsed["prioritize_count"],
                "global_fallback_count": parsed["global_fallback_count"],
                "verifier_switch_count": parsed["verifier_switch_count"],
                "detection_count": parsed["detection_count"],
                "verification_state_count": parsed["verification_state_count"],
            }
        )

os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
with open(OUT_CSV, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def stats(config_name, field):
    values = []
    for row in rows:
        if row["config"] != config_name:
            continue
        value = row[field]
        if value not in ("", None):
            values.append(float(value))
    return {
        "values": values,
        "mean": st.mean(values),
        "median": st.median(values),
        "std": st.stdev(values) if len(values) > 1 else 0.0,
    }


groups = [
    ("目标先验", "prior_on_east", "prior_off_east"),
    ("无进展换人", "handoff_on", "handoff_off"),
    ("多帧确认", "confirm_3frame", "confirm_1frame"),
]

fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.4), dpi=160, gridspec_kw={"width_ratios": [1.45, 1]})

# 左图：组件开/关的 wall time；散点保留全部三轮结果。
ax = axes[0]
x = np.arange(len(groups))
width = 0.32
colors = ["#1a73e8", "#9aa0a6"]
for offset, side, color in zip((-width / 2, width / 2), (1, 2), colors):
    means = []
    for _, on_name, off_name in groups:
        config_name = on_name if side == 1 else off_name
        means.append(stats(config_name, "wall_s")["mean"])
    bars = ax.bar(x + offset, means, width, color=color, alpha=0.9)
    for idx, (_, on_name, off_name) in enumerate(groups):
        config_name = on_name if side == 1 else off_name
        values = stats(config_name, "wall_s")["values"]
        jitter = np.linspace(-0.055, 0.055, len(values))
        ax.scatter(
            np.full(len(values), x[idx] + offset) + jitter,
            values,
            s=22,
            color="#202124",
            zorder=3,
        )
        ax.text(
            bars[idx].get_x() + bars[idx].get_width() / 2,
            bars[idx].get_height() / 2,
            f"{bars[idx].get_height():.1f}",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
        )
ax.set_xticks(x)
ax.set_xticklabels([name for name, _, _ in groups])
ax.set_ylabel("触发到三机 HALT 的 wall time（秒）")
ax.set_ylim(0, 72)
ax.grid(axis="y", alpha=0.25)
ax.set_title("组件开/关对照（柱为均值，点为本轮结果）", fontsize=11)
ax.legend(
    handles=[Patch(color=colors[0], label="开启"), Patch(color=colors[1], label="关闭")],
    frameon=False,
    loc="upper left",
)
ax.text(
    2,
    66,
    "单帧更快但不代表更安全",
    ha="center",
    fontsize=9,
    color="#d93025",
)

# 右图：确认后是否停止，统计从确认到三机 HALT 的延迟。
ax = axes[1]
labels = ["确认后停止", "确认后继续"]
config_names = ["stop_on", "stop_off"]
means = [stats(name, "confirm_to_halt_s")["mean"] for name in config_names]
bar_colors = ["#1a73e8", "#e37400"]
bars = ax.bar(labels, means, color=bar_colors, width=0.56)
for idx, config_name in enumerate(config_names):
    values = stats(config_name, "confirm_to_halt_s")["values"]
    jitter = np.linspace(-0.07, 0.07, len(values))
    ax.scatter(np.full(len(values), idx) + jitter, values, color="#202124", s=24, zorder=3)
    ax.text(
        idx,
        bars[idx].get_height() + 2.0,
        f"{bars[idx].get_height():.1f}s",
        ha="center",
        fontsize=10,
    )
ax.set_ylabel("确认后到三机 HALT 的延迟（秒）")
ax.set_ylim(0, 85)
ax.grid(axis="y", alpha=0.25)
ax.set_title("停止策略：目标确认后的额外探索时间", fontsize=11)

fig.suptitle("office2 目标触发式搜索组件消融", fontsize=15, y=0.985)
fig.text(
    0.5,
    0.018,
    "每组3轮；先验组使用东侧目标(5,5)，其余组使用中心目标(1,3)。仅作机制验证，不作统计显著性结论。",
    ha="center",
    fontsize=9,
    color="#5f6368",
)
fig.tight_layout(rect=(0, 0.055, 1, 0.95))
fig.savefig(OUT_PNG, dpi=300, facecolor="white")
plt.close(fig)

print(f"WROTE {OUT_CSV}")
print(f"WROTE {OUT_PNG}")
for name, on_label, off_label in (
    ("目标先验", "prior_on_east", "prior_off_east"),
    ("无进展换人", "handoff_on", "handoff_off"),
    ("多帧确认", "confirm_3frame", "confirm_1frame"),
):
    on_stats = stats(on_label, "wall_s")
    off_stats = stats(off_label, "wall_s")
    print(
        f"{name}: on mean={on_stats['mean']:.1f}s median={on_stats['median']:.1f}s; "
        f"off mean={off_stats['mean']:.1f}s median={off_stats['median']:.1f}s"
    )
for name in ("stop_on", "stop_off"):
    summary = stats(name, "confirm_to_halt_s")
    print(f"{name}: confirm_to_halt mean={summary['mean']:.1f}s values={summary['values']}")
