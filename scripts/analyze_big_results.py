#!/usr/bin/env python3
"""汇总大场景 A/B/C 批跑结果：均值±std、协同 vs 独立对比、柱状图
用法: analyze_big_results.py [结果文件] [场景名] [输出目录]
"""
import os
import re
import statistics as st
import sys
from collections import defaultdict

RES = sys.argv[1] if len(sys.argv) > 1 else '/mnt/d/WSL/multi_big_results.txt'
SCEN = sys.argv[2] if len(sys.argv) > 2 else 'office2'
OUTDIR = sys.argv[3] if len(sys.argv) > 3 else '/mnt/d/WSL/big_analysis'

RE_T = re.compile(r'\[(\w+)-(\w+)-(\d+)\] \[Flight_time\]: ([\d.]+) \(drone (\d)\)')
RE_D = re.compile(r'\[(\w+)-(\w+)-(\d+)\] \[Flight_dist\]: ([\d.]+) \(drone (\d)\)')
RE_W = re.compile(r'--- \[(\w+)-(\w+) RUN (\d+)\] wall_total=(\d+)s')


def load(path):
    t_ = defaultdict(dict)   # (mode, run, drone) -> time
    d_ = defaultdict(dict)
    wall = {}
    for line in open(path, errors='replace'):
        m = RE_T.search(line)
        if m and m.group(1) == SCEN:
            t_[(m.group(2), int(m.group(3)))][int(m.group(5))] = float(m.group(4))
        m = RE_D.search(line)
        if m and m.group(1) == SCEN:
            d_[(m.group(2), int(m.group(3)))][int(m.group(5))] = float(m.group(4))
        m = RE_W.search(line)
        if m and m.group(1) == SCEN:
            wall[(m.group(2), int(m.group(3)))] = int(m.group(4))
    return t_, d_, wall


def fmt(v):
    return f'{st.mean(v):.1f} ± {st.pstdev(v):.1f} (n={len(v)})' if v else '-'


def main():
    t_, d_, wall = load(RES)
    os.makedirs(OUTDIR, exist_ok=True)
    out_lines = []
    summary = {}
    print(f'==== {SCEN} 大场景实验汇总 ====')
    for mode in ('A', 'B', 'C'):
        runs = sorted(r for (m, r) in t_.keys() if m == mode)
        per_drone_t, per_drone_d = [], []
        walls, drone_means = [], []
        full_rounds = 0
        for r in runs:
            ts = list(t_[(mode, r)].values())
            ds = list(d_[(mode, r)].values())
            need = 1 if mode == 'A' else 3
            if len(ts) >= need:
                full_rounds += 1
                drone_means.append(st.mean(ts))
                per_drone_t += ts
                per_drone_d += ds
            if (mode, r) in wall:
                walls.append(wall[(mode, r)])
        line = (f'{mode}: 完整轮 {full_rounds}/{len(runs)} | 单机飞行时间均值 {fmt(drone_means)} | '
                f'单机航程 {fmt(per_drone_d)} | 每轮总时长 {fmt(walls)}s')
        print(line)
        out_lines.append(line)
        summary[mode] = dict(rounds=len(runs), full=full_rounds, drone_t=drone_means,
                             dists=per_drone_d, walls=walls)

    if 'B' in summary and 'C' in summary and summary['C']['full'] and summary['B']['full']:
        print('\n==== 协同(C) vs 独立(B) ====')
        for key, label in (('drone_t', '单机飞行时间'), ('walls', '每轮总时长')):
            b, c = summary['B'][key], summary['C'][key]
            if b and c:
                delta = (st.mean(c) - st.mean(b)) / st.mean(b) * 100
                line = f'{label}: 独立 {st.mean(b):.1f} vs 协同 {st.mean(c):.1f} （{delta:+.1f}%）'
                print(line)
                out_lines.append(line)

    with open(os.path.join(OUTDIR, f'summary_{SCEN}.txt'), 'w') as f:
        f.write('\n'.join(out_lines) + '\n')

    try:
        sys.path.insert(0, '/mnt/d/WSL')
        import importlib.util
        spec = importlib.util.spec_from_file_location('aep', '/mnt/d/WSL/analyze_edge_priority.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.setup_matplotlib_font()
        import matplotlib.pyplot as plt

        modes = [mo for mo in ('A', 'B', 'C') if summary[mo]['drone_t']]
        x = range(len(modes))
        fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
        for ax, key, title, unit in (
                (axes[0], 'drone_t', '单机飞行时间', 's'),
                (axes[1], 'dists', '单机航程', 'm'),
                (axes[2], 'walls', '每轮总时长 (wall)', 's')):
            vals = [summary[mo][key] for mo in modes]
            means = [st.mean(v) if v else 0 for v in vals]
            stds = [st.pstdev(v) if len(v) > 1 else 0 for v in vals]
            bars = ax.bar([f'{mo}' for mo in modes], means, yerr=stds, capsize=4,
                          color=['#9aa0a6', '#1a73e8', '#188038'][:len(modes)])
            for b, v in zip(bars, means):
                ax.text(b.get_x() + b.get_width() / 2, v, f'{v:.0f}', ha='center', va='bottom', fontsize=10)
            ax.set_title(f'{title} ({unit})')
            ax.grid(alpha=0.3, axis='y')
        fig.suptitle(f'A/B/C 对比（{SCEN} 场景）：A=单机 / B=三机独立 / C=三机协同', fontsize=13, y=0.99)
        fig.tight_layout(rect=[0, 0, 1, 0.93])
        p = os.path.join(OUTDIR, f'fig_big_{SCEN}.png')
        fig.savefig(p, dpi=150)
        print(f'图已保存：{p}')
    except Exception as e:
        print(f'绘图跳过（{e}）')


if __name__ == '__main__':
    main()
