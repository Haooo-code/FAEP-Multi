#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告配图：①系统架构 ②扇区分区示意 ③v1 散装 vs v2 分区（真实任务分配数据）"""
import importlib.util
import os
import re

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

spec = importlib.util.spec_from_file_location('aep', '/mnt/d/WSL/analyze_edge_priority.py')
_aep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_aep)
_aep.setup_matplotlib_font()
plt.rcParams['axes.unicode_minus'] = False

OUT = '/mnt/d/WSL/report_figs'
os.makedirs(OUT, exist_ok=True)

# ---------------- ① 架构图 ----------------
def fig_arch():
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    ax.set_facecolor('white')

    def box(x0, y0, w, h, title, body, fc='#EAF1FB', ec='#1a73e8'):
        ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle='round,pad=0.6,rounding_size=1.2',
                                    fc=fc, ec=ec, lw=1.4))
        ax.text(x0 + w / 2, y0 + h - 3.2, title, ha='center', va='top', fontsize=11, weight='bold')
        ax.text(x0 + w / 2, y0 + h - 7.4, body, ha='center', va='top', fontsize=8.2, linespacing=1.5)

    box(18, 77, 64, 20, '协调器 faep_coordinator',
        '任务池（空间合并 1.5m） ｜ 扇区归属分配 ｜ 租约 60s\n'
        '统一 HALT 收尾 ｜ 卡住检测与任务自愈', fc='#E8F5E9', ec='#188038')
    ax.text(50, 87.5, '', ha='center')

    drones = [('无人机 1', 3), ('无人机 2', 36.5), ('无人机 3', 70)]
    for name, x in drones:
        box(x, 38, 27, 26, name,
            'FAEP 单机栈\n深度相机 → SDF 建图\n前沿检测 → 视点 → LKH 巡游\nB 样条轨迹 + 控制')

    # 快照（上箭头）
    for _, x in drones:
        ax.annotate('', xy=(x + 13.5, 76.5), xytext=(x + 13.5, 64.5),
                    arrowprops=dict(arrowstyle='-|>', color='#1a73e8', lw=1.6))
    ax.text(9.5, 70.6, '前沿快照 5Hz', fontsize=8, color='#1a73e8')

    # 分配（下箭头，绿色）
    for _, x in drones:
        ax.annotate('', xy=(x + 20, 64.5), xytext=(x + 20, 76.5),
                    arrowprops=dict(arrowstyle='-|>', color='#188038', lw=1.6))
    ax.text(79.5, 70.6, '任务分配 / 扇区', fontsize=8, color='#188038', ha='right')

    # HALT（红色虚线）
    for _, x in drones:
        ax.annotate('', xy=(x + 9, 64.5), xytext=(x + 9, 76.5),
                    arrowprops=dict(arrowstyle='-|>', color='#d93025', lw=1.3, ls='dashed'))
    ax.text(41.5, 70.0, 'HALT', fontsize=8, color='#d93025')

    # 仿真底栏
    ax.add_patch(FancyBboxPatch((3, 8), 94, 16, boxstyle='round,pad=0.6,rounding_size=1.2',
                                fc='#F1F3F4', ec='#5f6368', lw=1.2))
    ax.text(50, 19.5, '仿真环境：3 × uav_simulator（共享真值地图 + CUDA 深度相机）',
            ha='center', va='top', fontsize=9.5)
    for _, x in drones:
        ax.annotate('', xy=(x + 13.5, 37.6), xytext=(x + 13.5, 24.6),
                    arrowprops=dict(arrowstyle='-|>', color='#5f6368', lw=1.2))
    ax.text(6.2, 29.5, '深度图像 / 里程计', fontsize=7.8, color='#5f6368')

    ax.set_title('FAEP-Multi 系统架构：三机各自保留完整单机栈，协调器只做任务层协同',
                 fontsize=12.5, pad=6)
    fig.tight_layout()
    p = os.path.join(OUT, 'fig_arch.png')
    fig.savefig(p, dpi=300, facecolor='white')
    plt.close(fig)
    print('WROTE', p)


# ---------------- 地图与扇区 ----------------
OFFICE2_PCD = '/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource/office2.pcd'
STARTS = {1: (-7.5, -3.5), 2: (4.5, -3.5), 3: (-3.5, 6.5)}
MARK = {1: 'o', 2: 's', 3: '^'}
SECTOR_B = (-5.5, 0.5)   # 分界（axis=x）
OWNER_RANGES = {1: (-10.4, -5.5), 3: (-5.5, 0.5), 2: (0.5, 10.4)}
COL = {1: '#1a73e8', 2: '#e8710a', 3: '#188038'}


def load_pcd_xy():
    xs, ys = [], []
    with open(OFFICE2_PCD) as f:
        for line in f:
            if line[:1] in '#VSCWHPD':
                continue
            p = line.split()
            if len(p) == 3:
                xs.append(float(p[0]))
                ys.append(float(p[1]))
    return np.array(xs), np.array(ys)


def draw_map(ax, xs, ys):
    ax.scatter(xs, ys, s=0.12, c='#80868b', alpha=0.5, linewidths=0)
    ax.set_xlim(-10.6, 10.6)
    ax.set_ylim(-10.6, 10.6)
    ax.set_aspect('equal')
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color('#5f6368')


def fig_partition(xs, ys):
    fig, ax = plt.subplots(figsize=(6.4, 6.2))
    draw_map(ax, xs, ys)
    for owner, (lo, hi) in OWNER_RANGES.items():
        ax.axvspan(lo, hi, color=COL[owner], alpha=0.10, zorder=0)
    for b in SECTOR_B:
        ax.axvline(b, color='#202124', lw=1.2, ls='--')
    for d, (x, y) in STARTS.items():
        ax.scatter([x], [y], s=140, marker=MARK[d], c=COL[d],
                   edgecolors='white', linewidths=1.4, zorder=5)
        ax.annotate(f'D{d}  ({x:.1f}, {y:.1f})', (x, y), textcoords='offset points',
                    xytext=(8, 10), fontsize=9, color=COL[d], weight='bold')
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker=MARK[d], color='w', markerfacecolor=COL[d],
                      markersize=8, label=f'D{d} 起始点') for d in (1, 2, 3)]
    ax.legend(handles=handles, loc='lower right', fontsize=8, frameon=False)
    ax.text(-7.9, 9.4, '扇区 A（D1）', fontsize=9, color=COL[1], ha='center')
    ax.text(-2.5, 9.4, '扇区 B（D3）', fontsize=9, color=COL[3], ha='center')
    ax.text(5.4, 9.4, '扇区 C（D2）', fontsize=9, color=COL[2], ha='center')
    ax.set_title('office2（20×20m）：按初始位置划分的 Voronoi 扇区', fontsize=11.5, pad=8)
    fig.tight_layout()
    p = os.path.join(OUT, 'fig_partition.png')
    fig.savefig(p, dpi=300, facecolor='white')
    plt.close(fig)
    print('WROTE', p)


def parse_v1(log_path):
    centers, last_owner, n_assign = {}, {}, 0
    for line in open(log_path, errors='replace'):
        m = re.search(r'new task #(\d+) from drone\d at \(([-\d.]+), ([-\d.]+),', line)
        if m:
            centers[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
            continue
        m = re.search(r'assign task #(\d+) -> drone(\d+)', line)
        if m:
            last_owner[int(m.group(1))] = int(m.group(2))
            n_assign += 1
    return centers, last_owner, n_assign


def fig_v1v2(xs, ys, log_path):
    centers, last_owner, n_assign = parse_v1(log_path)
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 5.8))
    for ax in axes:
        draw_map(ax, xs, ys)

    ax = axes[0]
    from collections import Counter
    cnt = Counter()
    for tid, (x, y) in centers.items():
        owner = last_owner.get(tid)
        if owner in COL:
            ax.scatter([x], [y], s=26, c=COL[owner], alpha=0.85, edgecolors='white', linewidths=0.4)
            cnt[owner] += 1
    ax.set_title(f'v1：任务按"最近机"分配 → 散装\n'
                 f'{len(centers)} 个任务中心，被分配 {n_assign} 次', fontsize=10.5)
    for d in (1, 2, 3):
        x, y = STARTS[d]
        ax.scatter([x], [y], s=120, marker='*', c=COL[d], edgecolors='white', linewidths=1.0, zorder=6)
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker='o', color='w', markerfacecolor=COL[d],
                      markersize=6, label=f'D{d} 名下任务') for d in (1, 2, 3)]
    ax.legend(handles=handles, loc='lower right', fontsize=8, frameon=False)
    ax.text(-10.2, -10.2, 'D1 / D2 / D3 的颜色：任务最终归属机', fontsize=8, color='#5f6368')

    ax = axes[1]
    for owner, (lo, hi) in OWNER_RANGES.items():
        ax.axvspan(lo, hi, color=COL[owner], alpha=0.12, zorder=0)
    for b in SECTOR_B:
        ax.axvline(b, color='#202124', lw=1.2, ls='--')
    for d, (x, y) in STARTS.items():
        ax.scatter([x], [y], s=120, marker='*', c=COL[d], edgecolors='white', linewidths=1.0, zorder=6)
    handles = [Line2D([0], [0], marker='*', color='w', markerfacecolor=COL[d],
                      markersize=10, label=f'D{d} 扇区') for d in (1, 2, 3)]
    ax.legend(handles=handles, loc='lower right', fontsize=8, frameon=False)
    ax.set_title('v2：按初始位置划分扇区 → 每机一块\n'
                 '任务创建即归属扇区机，不再重派', fontsize=10.5)
    ax.text(-10.2, -10.2, '扇区即任务白名单；快照只上报本扇区前沿', fontsize=8, color='#5f6368')

    fig.suptitle('协同机制对比：v1 的"散装分配" vs v2 的"空间分区"（office2 实测日志）',
                 fontsize=12, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    p = os.path.join(OUT, 'fig_v1_vs_v2.png')
    fig.savefig(p, dpi=300, facecolor='white')
    plt.close(fig)
    print('WROTE', p, f'(tasks={len(centers)}, assigns={n_assign})')


if __name__ == '__main__':
    xs, ys = load_pcd_xy()
    fig_arch()
    fig_partition(xs, ys)
    log = '/mnt/d/WSL/multi_office2v1C_run1.log'
    if os.path.exists(log):
        fig_v1v2(xs, ys, log)
    else:
        print('v1 log missing:', log)
