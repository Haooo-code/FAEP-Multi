#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 覆盖分析（可调轨迹扩张半径）：analyze_coverage.py 的加强版
# 用法: analyze_coverage2.py <track.csv> <map.pcd> [radius_m]
import csv
import sys

import numpy as np

track = sys.argv[1]
pcd = sys.argv[2]
RAD = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
GRID = 1.0

px, py = [], []
with open(pcd) as f:
    for line in f:
        if line[0] in '#VSCWHPD':
            continue
        p = line.split()
        if len(p) == 3:
            px.append(float(p[0])); py.append(float(p[1]))
px = np.array(px); py = np.array(py)
x_min, x_max = np.floor(px.min()), np.ceil(px.max())
y_min, y_max = np.floor(py.min()), np.ceil(py.max())

occ = set()
for x, y in zip(px, py):
    occ.add((int(np.floor(x / GRID)), int(np.floor(y / GRID))))

free = set()
for gx in range(int(x_min), int(x_max) + 1):
    for gy in range(int(y_min), int(y_max) + 1):
        if (gx, gy) not in occ:
            free.add((gx, gy))

k = int(round(RAD / GRID))
tracks = {1: set(), 2: set(), 3: set()}
with open(track) as f:
    r = csv.DictReader(f)
    for row in r:
        for i in (1, 2, 3):
            x = float(row['d%dx' % i]); y = float(row['d%dy' % i])
            gx, gy = int(np.floor(x / GRID)), int(np.floor(y / GRID))
            for dx in range(-k, k + 1):
                for dy in range(-k, k + 1):
                    c = (gx + dx, gy + dy)
                    if c in free:
                        tracks[i].add(c)

union = tracks[1] | tracks[2] | tracks[3]
multi = (tracks[1] & tracks[2]) | (tracks[1] & tracks[3]) | (tracks[2] & tracks[3])
print(f'R={RAD:.1f}m  free={len(free)}  '
      f'd1={len(tracks[1])} d2={len(tracks[2])} d3={len(tracks[3])}  '
      f'union={len(union)} ({100.0 * len(union) / max(1, len(free)):.1f}%)  '
      f'multi={len(multi)} ({100.0 * len(multi) / max(1, len(union)):.1f}% of union)')
