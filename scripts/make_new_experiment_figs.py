#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2026-10-18 增量实验配图：等面积对照 / 故障恢复 / 收益边界。"""

import importlib.util
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

spec = importlib.util.spec_from_file_location("aep", "/mnt/d/WSL/analyze_edge_priority.py")
_aep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_aep)
_aep.setup_matplotlib_font()
plt.rcParams["axes.unicode_minus"] = False

OUT = "/mnt/d/WSL/new_figs"
os.makedirs(OUT, exist_ok=True)

BLUE = "#1a73e8"
BLACK = "#202124"
GRAY = "#9aa0a6"
GREEN = "#188038"
RED = "#d93025"


def fig_equal_area():
    # 6 组交替配对：V=Voronoi，E=严格等面积；数值来自 multi_big_results.txt
    v_mean = np.array([64.9, 80.6, 58.4, 69.6, 77.0, 64.1])
    e_mean = np.array([53.7, 53.6, 62.4, 73.2, 52.0, 62.2])
    v_wall = np.array([72, 87, 66, 76, 84, 73])
    e_wall = np.array([61, 60, 69, 81, 60, 69])
    # 自由区面积（0.2m 障碍膨胀）
    schemes = ["Voronoi\n(中点分界)", "等宽\n(交接原口径)", "等面积\n(自由区均衡)"]
    areas = np.array([
        [71.5, 95.4, 139.3],
        [99.1, 110.7, 96.5],
        [99.1, 103.6, 103.6],
    ])
    imbalance = [66.5, 13.9, 4.4]

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.0))
    ax = axes[0]
    x = np.arange(len(v_mean))
    ax.plot(x, v_mean, "o-", color=GRAY, lw=2, ms=6, label="Voronoi（当前 v2）")
    ax.plot(x, e_mean, "o-", color=BLUE, lw=2, ms=6, label="严格等面积")
    for i in range(len(x)):
        ax.plot([x[i], x[i]], [v_mean[i], e_mean[i]], color=BLACK, lw=0.8, alpha=0.25)
    ax.set_xticks(x)
    ax.set_xticklabels([f"配对 {i+1}" for i in x])
    ax.set_ylabel("单机飞行时间均值 (s)")
    ax.set_title("office2：6 组交替配对（等面积 4/6 更快，但方差大）", fontsize=11)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(frameon=False, fontsize=9)

    ax = axes[1]
    x = np.arange(3)
    w = 0.24
    labels = ["D1 西区", "D3 中区", "D2 东区"]
    for j, name in enumerate(schemes):
        bars = ax.bar(x + (j - 1) * w, areas[j], w, label=name)
        for b, val in zip(bars, areas[j]):
            ax.text(b.get_x() + b.get_width() / 2, val + 2, f"{val:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("扇区自由区面积 (m²)")
    ax.set_ylim(0, 160)
    ax.set_title("等面积把 D1 从 72 m² 扩到 99 m²，瓶颈机反而更重", fontsize=11)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(frameon=False, fontsize=8, loc="upper left")

    fig.suptitle("等面积扇区实验：分界更均衡，但不等于完成时间更短", fontsize=13, y=0.99)
    fig.text(0.5, 0.012, "6 组配对：中位差 −6.5 s，均值差 −9.6 s，95% 区间跨 0；"
                         "面积不均衡度 66.5% → 4.4%，但 D1 仍是最慢机。",
             ha="center", fontsize=9, color=RED)
    fig.tight_layout(rect=[0, 0.04, 1, 0.93])
    path = os.path.join(OUT, "fig_equal_area_office2.png")
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    print("WROTE", path)


def fig_fault():
    # 三次故障轮（kill D3 @ +41s）；数据来自 fault_results.txt 与覆盖分析
    walls = [146, 173, 165]
    kill_at = 41
    loss_at = [51, 50, 49]
    sweep_at = [117, 114, 132]
    released = [14, 7, 5]
    pre = [49, 51, 45]
    post = [72, 68, 70]
    total_sector = 88

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    ax = axes[0]
    for i, (wall, loss, sweep) in enumerate(zip(walls, loss_at, sweep_at)):
        y = 2 - i
        ax.broken_barh([(0, kill_at)], (y - 0.22, 0.44), facecolors="#e8f0fe")
        ax.broken_barh([(kill_at, loss - kill_at)], (y - 0.22, 0.44), facecolors="#fce8e6")
        ax.broken_barh([(loss, sweep - loss)], (y - 0.22, 0.44), facecolors="#e6f4ea")
        ax.broken_barh([(sweep, wall - sweep)], (y - 0.22, 0.44), facecolors="#fef7e0")
        ax.text(wall + 2, y, f"{wall}s", va="center", fontsize=9)
    ax.axvline(kill_at, color=RED, lw=1.4, ls="--")
    ax.text(kill_at + 1, 2.40, "kill D3", color=RED, fontsize=9)
    ax.set_yticks([2, 1, 0])
    ax.set_yticklabels(["轮 1", "轮 2", "轮 3"])
    ax.set_xlim(0, 195)
    ax.set_ylim(-0.6, 2.7)
    ax.set_xlabel("触发后时间 (s)")
    ax.set_title("故障时间线：检测 → 任务重派 → 全局扫尾 → 统一 HALT", fontsize=11)
    ax.grid(alpha=0.3, axis="x")
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(color="#e8f0fe", label="故障前"),
        Patch(color="#fce8e6", label="失联检测"),
        Patch(color="#e6f4ea", label="任务级接管"),
        Patch(color="#fef7e0", label="全局扫尾"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.20), ncol=4, frameon=False, fontsize=8)

    ax = axes[1]
    x = np.arange(3)
    w = 0.34
    ax.bar(x - w / 2, pre, w, label="故障前已覆盖", color=GRAY)
    ax.bar(x + w / 2, post, w, label="故障后（含幸存机新增）", color=GREEN)
    for i in range(3):
        ax.text(x[i] + w / 2, post[i] + 1.5, f"{post[i]}/{total_sector}", ha="center", fontsize=9)
        ax.text(x[i] + w / 2, post[i] / 2, f"+{post[i]-pre[i]}", ha="center", color="white", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"轮 {i+1}\n释放 {released[i]} 任务" for i in range(3)])
    ax.set_ylim(0, 100)
    ax.set_ylabel("D3 扇区覆盖格数（1m 邻域）")
    ax.set_title("失联扇区覆盖：77–82%，幸存机新增 17–25 格", fontsize=11)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)

    fig.suptitle("故障注入：kill -9 中间机，租约释放后由两架幸存机接管并统一收尾", fontsize=13, y=0.99)
    fig.tight_layout(rect=[0, 0.12, 1, 0.93])
    path = os.path.join(OUT, "fig_fault_recovery.png")
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    print("WROTE", path)


def fig_boundary():
    # 冻结数据表（2026-10-17）：A/B/C 单机时间
    scenes = ["office", "office2", "office3"]
    free_area = np.array([362.4, 306.2, 445.1])
    aspect = np.array([30 / 16, 1.0, 28.8 / 19.7])
    b_over_c = np.array([167.2 / 94.0, 132.9 / 66.4, 161.9 / 90.7])
    a_over_c = np.array([142.5 / 94.0, 109.3 / 66.4, 148.3 / 90.7])

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.6))
    for ax, x, xlabel, title in (
        (axes[0], free_area, "自由区面积 (m²)", "协同加速比 vs 地图面积"),
        (axes[1], aspect, "长宽比（长边/短边）", "协同加速比 vs 场景长宽比"),
    ):
        ax.plot(x, b_over_c, "o-", color=BLUE, lw=2, ms=8, label="B/C（三机独立 / 协同）")
        ax.plot(x, a_over_c, "s--", color=GRAY, lw=1.6, ms=6, label="A/C（单机 / 协同）")
        for xi, yi, name in zip(x, b_over_c, scenes):
            ax.annotate(name, (xi, yi), textcoords="offset points", xytext=(6, 8), fontsize=9)
        ax.axhline(1.0, color=BLACK, lw=0.8, alpha=0.5)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("加速比（>1 表示协同更快）")
        ax.set_title(title, fontsize=11)
        ax.set_ylim(0.9, 2.25)
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("收益边界：3 个场景呈非单调关系，面积本身不足以解释加速比", fontsize=13, y=0.99)
    fig.text(0.5, 0.01, "office2 面积最小但加速比最高；office3 面积最大但回落到 office 水平。"
                        "结论仅作趋势分析，3 个场景不足以拟合边界。",
             ha="center", fontsize=9, color=RED)
    fig.tight_layout(rect=[0, 0.05, 1, 0.93])
    path = os.path.join(OUT, "fig_benefit_boundary.png")
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)
    print("WROTE", path)


if __name__ == "__main__":
    fig_equal_area()
    fig_fault()
    fig_boundary()
