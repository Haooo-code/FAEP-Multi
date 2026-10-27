#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 5Hz 轨迹数据离线渲染"三机扇区协同"演示视频（30fps，含地图/扇区/轨迹/结尾数据卡）"""
import csv
import subprocess

from PIL import Image, ImageDraw, ImageFont

PCD = '/home/ubuntu/catkin_ws/src/faep/uav_simulator/map_generator/resource/office2.pcd'
TRACK = '/mnt/d/WSL/track_office2_C_1.csv'
OUT = '/mnt/d/WSL/multi_video/multi_sector.mp4'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

W, H = 1280, 720
MAP_PX = 660
OX, OY = 30, 40
SCALE = MAP_PX / 21.2          # 21.2m 覆盖
CX, CY = 0.0, 0.0              # 世界坐标中心
COL = {1: (26, 115, 232), 2: (232, 113, 10), 3: (24, 128, 56)}
SECT = {1: (-10.6, -5.5), 2: (0.5, 10.6), 3: (-5.5, 0.5)}   # owner -> (lo, hi)

font_big = ImageFont.truetype(FONT, 30)
font = ImageFont.truetype(FONT, 20)
font_small = ImageFont.truetype(FONT, 16)


def w2p(x, y):
    px = OX + (x - CX) * SCALE + MAP_PX / 2
    py = OY + MAP_PX / 2 - (y - CY) * SCALE
    return px, py


def load_map():
    xs, ys = [], []
    with open(PCD) as f:
        for line in f:
            if line[:1] in '#VSCWHPD':
                continue
            p = line.split()
            if len(p) == 3:
                xs.append(float(p[0]))
                ys.append(float(p[1]))
    return xs, ys


def base_image(xs, ys):
    img = Image.new('RGB', (W, H), (250, 250, 250))
    d = ImageDraw.Draw(img, 'RGBA')
    # 扇区底色
    for owner, (lo, hi) in SECT.items():
        x0, y0 = w2p(lo, 10.6)
        x1, y1 = w2p(hi, -10.6)
        c = COL[owner] + (26,)
        d.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=c)
    # 墙体点
    for x, y in zip(xs, ys):
        px, py = w2p(x, y)
        if OX - 5 <= px <= OX + MAP_PX + 5 and OY - 5 <= py <= OY + MAP_PX + 5:
            d.point((px, py), fill=(120, 124, 130))
    # 扇区分界
    for b in (-5.5, 0.5):
        x0, y0 = w2p(b, 10.6)
        x1, y1 = w2p(b, -10.6)
        d.line([x0, y0, x1, y1], fill=(60, 64, 72), width=2)
    # 地图边框
    d.rectangle([OX, OY, OX + MAP_PX, OY + MAP_PX], outline=(90, 94, 100), width=2)
    # 扇区标签
    NAME = {1: 'A', 3: 'B', 2: 'C'}   # 与文档一致：D1 西=A, D3 中=B, D2 东=C
    for owner, (lo, hi) in SECT.items():
        cx = (lo + hi) / 2
        px, py = w2p(cx, 9.9)
        d.text((px, py), f"扇区 {NAME[owner]}", font=font, fill=COL[owner],
               anchor='mm')
    # 标题
    d.text((30, 8), "三机扇区协同探索 · office2（20×20m）· 每机只扫自己的扇区", font=font_big,
           fill=(32, 33, 36))
    return img


def load_track():
    rows = []
    with open(TRACK) as f:
        for r in csv.DictReader(f):
            rows.append({
                't': float(r['t']),
                1: (float(r['d1x']), float(r['d1y'])),
                2: (float(r['d2x']), float(r['d2y'])),
                3: (float(r['d3x']), float(r['d3y'])),
            })
    return rows


def pos_at(rows, T, drone):
    if T <= rows[0]['t']:
        return rows[0][drone]
    if T >= rows[-1]['t']:
        return rows[-1][drone]
    for i in range(1, len(rows)):
        if rows[i]['t'] >= T:
            t0, t1 = rows[i - 1]['t'], rows[i]['t']
            a, b = rows[i - 1][drone], rows[i][drone]
            k = (T - t0) / max(1e-6, t1 - t0)
            return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    return rows[-1][drone]


def main():
    xs, ys = load_map()
    rows = load_track()
    dur = rows[-1]['t']
    fps = 30
    intro, outro = 1.5, 2.5
    base = base_image(xs, ys)

    ff = subprocess.Popen([
        'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
        '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)

    total = int((intro + dur + outro) * fps)
    for k in range(total):
        t = k / fps
        img = base.copy()
        d = ImageDraw.Draw(img)
        if t < intro:
            # 开场：静态地图 + 提示
            d.text((OX + MAP_PX / 2, OY + MAP_PX - 40), "3 架无人机 · 同时起飞 · 各扫一块",
                   font=font_big, fill=(32, 33, 36), anchor='mm')
        elif t < intro + dur:
            T = t - intro
            for dr in (1, 2, 3):
                pts = [w2p(*r[dr]) for r in rows if r['t'] <= T]
                p = pos_at(rows, T, dr)
                pts.append(w2p(*p))
                if len(pts) >= 2:
                    d.line(pts, fill=COL[dr], width=3, joint='curve')
            for dr in (1, 2, 3):
                p = pos_at(rows, T, dr)
                px, py = w2p(*p)
                d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=COL[dr], outline=(255, 255, 255),
                          width=2)
                d.text((px + 12, py - 12), f"D{dr}", font=font_small, fill=COL[dr])
            # 右侧面板
            d.text((740, 120), "实时状态", font=font_big, fill=(32, 33, 36))
            d.text((740, 170), f"时间  {T:5.1f} s", font=font, fill=(60, 64, 72))
            for dr in (1, 2, 3):
                p = pos_at(rows, T, dr)
                d.ellipse([740, 220 + (dr - 1) * 56, 760, 240 + (dr - 1) * 56], fill=COL[dr])
                d.text((772, 216 + (dr - 1) * 56),
                       f"D{dr}  ({p[0]:5.1f}, {p[1]:5.1f}) m", font=font, fill=(32, 33, 36))
            d.text((740, 420), "• 任务创建即归属扇区机，不再重派", font=font_small, fill=(60, 64, 72))
            d.text((740, 450), "• 每机只上报本扇区前沿", font=font_small, fill=(60, 64, 72))
            d.text((740, 480), "• 全部完成后统一 HALT 收尾", font=font_small, fill=(60, 64, 72))
        else:
            # 结尾数据卡
            for dr in (1, 2, 3):
                pts = [w2p(*r[dr]) for r in rows]
                if len(pts) >= 2:
                    d.line(pts, fill=COL[dr], width=3, joint='curve')
                px, py = w2p(*rows[-1][dr])
                d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=COL[dr], outline=(255, 255, 255),
                          width=2)
            d.rectangle([710, 90, 1250, 520], fill=(255, 255, 255, 235),
                        outline=(210, 213, 218), width=2)
            d.text((730, 135), "三机扇区协同 · 一轮结果", font=font_big, fill=(32, 33, 36))
            lines = [
                "单机飞行 66 s（独立 133 s，−50%）",
                "总时长   74 s（独立 168 s，−56%）",
                "重复覆盖 7.6%（独立 94%）",
                "三机各扫一块，统一 HALT 收尾",
            ]
            for i, ln in enumerate(lines):
                d.text((730, 215 + i * 62), ln, font=font, fill=(32, 33, 36))
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    print('WROTE', OUT, f'{total} frames, {intro + dur + outro:.1f}s')


if __name__ == '__main__':
    main()
