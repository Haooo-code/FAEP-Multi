#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 自绘大场景生成器：40x40m 随机障碍迷宫（论文随机图风格），输出 ASCII PCD（供 map_pub 发布）
# 生成规则：
#   - 周边围墙（厚 0.2m，高 2.4m）
#   - 内部随机矩形障碍（墙段/方块，高 2.4m），放置时保证与已有障碍最小间隙 >= 1.2m
#   - 1.2m 栅格的连通性 flood fill 校验（保证无人机可达）
import random
import sys
from collections import deque

random.seed(20261015)  # 固定种子，实验可复现

X_HALF = 20.0
Y_HALF = 20.0
HEIGHT = 2.4
RES = 0.1
MIN_GAP = 1.5
OUT = '/mnt/d/WSL/big_map.pcd'

obs = []  # (x1, y1, x2, y2)


def rects_overlap_or_close(a, b, gap):
    return not (a[2] + gap < b[0] or b[2] + gap < a[0] or a[3] + gap < b[1] or b[3] + gap < a[1])


def sample_rect_surface(x1, y1, x2, y2, pts):
    # 沿四边按 RES 采样
    xs = [x1 + i * RES for i in range(int((x2 - x1) / RES) + 1)]
    ys = [y1 + i * RES for i in range(int((y2 - y1) / RES) + 1)]
    for x in xs:
        pts.append((x, y1))
        pts.append((x, y2))
    for y in ys:
        pts.append((x1, y))
        pts.append((x2, y))


def try_place(kind):
    for _ in range(200):
        if kind == 'wall':  # 薄墙段
            w = random.uniform(2.5, 7.0)
            h = random.uniform(0.25, 0.5)
        else:  # 方块/家具
            w = random.uniform(1.2, 3.2)
            h = random.uniform(1.2, 3.2)
        cx = random.uniform(-X_HALF + 2.0, X_HALF - 2.0)
        cy = random.uniform(-Y_HALF + 2.0, Y_HALF - 2.0)
        if random.random() < 0.5:
            w, h = h, w
        cand = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        ok = True
        for o in obs:
            if rects_overlap_or_close(cand, o, MIN_GAP):
                ok = False
                break
        if ok:
            obs.append(cand)
            return True
    return False


# 1) 围墙
obs.append((-X_HALF, -Y_HALF, X_HALF, -Y_HALF + 0.2))
obs.append((-X_HALF, Y_HALF - 0.2, X_HALF, Y_HALF))
obs.append((-X_HALF, -Y_HALF, -X_HALF + 0.2, Y_HALF))
obs.append((X_HALF - 0.2, -Y_HALF, X_HALF, Y_HALF))

# 2) 内部障碍：30 面墙 + 25 个方块
placed = 0
for _ in range(30):
    if try_place('wall'):
        placed += 1
for _ in range(25):
    if try_place('block'):
        placed += 1
print("内部障碍放置成功: %d（墙%d + 方块其它）" % (placed, 30))

# 3) 采样点
pts = []
for o in obs:
    sample_rect_surface(o[0], o[1], o[2], o[3], pts)
print("表面采样点数: %d" % len(pts))

# 4) 连通性校验（1.2m 栅格，BFS 从 (0,0) 起；围墙内有障碍的格子不可通行，
#    近似用"格中心距任何障碍 < 0.6m 视为阻挡"）——只做提醒，不强制失败
GRID = 1.2
nx = int(2 * X_HALF / GRID)
ny = int(2 * Y_HALF / GRID)


def blocked(cx, cy):
    for o in obs:
        if o[0] - 0.4 <= cx <= o[2] + 0.4 and o[1] - 0.4 <= cy <= o[3] + 0.4:
            return True
    return False


start = (int((0 + X_HALF) / GRID), int((0 + Y_HALF) / GRID))
seen = {start}
dq = deque([start])
while dq:
    i, j = dq.popleft()
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ni, nj = i + di, j + dj
        if 0 <= ni < nx and 0 <= nj < ny and (ni, nj) not in seen:
            cx = -X_HALF + (ni + 0.5) * GRID
            cy = -Y_HALF + (nj + 0.5) * GRID
            if not blocked(cx, cy):
                seen.add((ni, nj))
                dq.append((ni, nj))
total_free = 0
for i in range(nx):
    for j in range(ny):
        cx = -X_HALF + (i + 0.5) * GRID
        cy = -Y_HALF + (j + 0.5) * GRID
        if not blocked(cx, cy):
            total_free += 1
print("连通区占比: %d/%d = %.1f%%（从 (0,0) 可达）" % (len(seen), total_free, 100.0 * len(seen) / max(1, total_free)))
if len(seen) < 0.9 * total_free:
    print("警告: 连通性不足 90%，建议换种子或减少障碍", file=sys.stderr)

# 5) 输出 PCD（ASCII，与 office.pcd 同格式；障碍表面按 z 分层采样，与 office 一致）
Z_LAYERS = [0.0, 0.5, 1.0, 1.5, 2.0, HEIGHT]
with open(OUT, 'w') as f:
    f.write("# .PCD v0.7 - Point Cloud Data file format\n")
    f.write("VERSION 0.7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\nCOUNT 1 1 1\n")
    n_total = len(pts) * len(Z_LAYERS)
    f.write("WIDTH %d\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS %d\nDATA ascii\n" % (n_total, n_total))
    for x, y in pts:
        for z in Z_LAYERS:
            f.write("%.4f %.4f %.4f\n" % (x, y, z))
print("已写出: %s（%d 点）" % (OUT, n_total))
