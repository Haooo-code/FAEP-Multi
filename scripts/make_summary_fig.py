#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三场景 A/B/C 汇总图（数据源：big_analysis/summary_<scene>.txt，由 analyze_big_results.py 生成）"""
import os
import re

import matplotlib

matplotlib.use('Agg')
import importlib.util

import matplotlib.pyplot as plt

spec = importlib.util.spec_from_file_location('aep', '/mnt/d/WSL/analyze_edge_priority.py')
_aep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_aep)
_aep.setup_matplotlib_font()

BASE = '/mnt/d/WSL/big_analysis'
SCENES = ['office', 'office2', 'office3']
TITLES = {'office': 'office 16×30m', 'office2': 'office2 20×20m', 'office3': 'office3 19.7×28.8m'}


def parse_summary(scene):
    path = os.path.join(BASE, f'summary_{scene}.txt')
    data = {}
    if not os.path.exists(path):
        return data
    for line in open(path):
        m = re.match(r'([ABC]): .*单机飞行时间均值 ([\d.]+) ± [\d.]+', line)
        w = re.search(r'每轮总时长 ([\d.]+|-)', line)
        if m:
            data[m.group(1)] = {'t': float(m.group(2)),
                                'wall': float(w.group(1)) if w and w.group(1) != '-' else None}
    return data


data = {s: parse_summary(s) for s in SCENES}
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
colors = {'A': '#9aa0a6', 'B': '#1a73e8', 'C': '#188038'}
width = 0.26
for ax, key, title in ((axes[0], 't', '单机飞行时间 (s)'), (axes[1], 'wall', '每轮总时长 wall (s)')):
    import numpy as np
    x = np.arange(len(SCENES))
    for j, mode in enumerate('ABC'):
        vals = [data[s].get(mode, {}).get(key) for s in SCENES]
        ys = [v if v is not None else 0 for v in vals]
        bars = ax.bar(x + (j - 1) * width, ys, width, label=mode, color=colors[mode])
        for b, v in zip(bars, vals):
            if v is None:
                ax.text(b.get_x() + b.get_width() / 2, 2, 'n/a', ha='center', va='bottom', fontsize=8)
            else:
                ax.text(b.get_x() + b.get_width() / 2, v, f'{v:.0f}', ha='center', va='bottom', fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([TITLES[s] for s in SCENES])
    ax.set_title(title)
    ax.grid(alpha=0.3, axis='y')
    ax.legend()
fig.suptitle('三场景对比：A 单机 / B 三机独立 / C 三机协同（扇区分区 v2.0）', fontsize=13, y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.93])
out = os.path.join(BASE, 'fig_summary_3scenes.png')
fig.savefig(out, dpi=150)
print('WROTE', out)
