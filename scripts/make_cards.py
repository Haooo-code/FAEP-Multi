#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成视频标题/信息卡（1920x1080，浅色，无学校信息）"""
import os

from PIL import Image, ImageDraw, ImageFont

OUT = '/mnt/d/WSL/cards'
os.makedirs(OUT, exist_ok=True)
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
W, H = 1920, 1080
BG = (250, 250, 247)
FG = (32, 33, 36)
BLUE = (26, 115, 232)
GREEN = (24, 128, 56)
GREY = (95, 99, 104)


def font(sz, bold=False):
    return ImageFont.truetype(FONT, sz)


def base():
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 18, H], fill=BLUE)
    return img, d


def cards():
    # 1 标题
    img, d = base()
    d.text((120, 330), 'FAEP-Multi', font=font(110), fill=FG)
    d.text((120, 480), '把开源单机自主探索算法，扩展为三机协同', font=font(52), fill=BLUE)
    d.text((120, 580), '扇区分工 · 统一收尾 · 可靠性加固 · 可复现评测', font=font(38), fill=GREY)
    img.save(f'{OUT}/card_01_title.png')

    # 2 问题
    img, d = base()
    d.text((120, 120), '问题：未知环境，要一次探完', font=font(64), fill=FG)
    lines = ['搜救、测绘、巡检：环境完全未知', '单机视野有限，一架飞机逐点探索很慢',
             '直接放三架？三架会重复扫同一片区域']
    for i, ln in enumerate(lines):
        d.ellipse([130, 300 + i * 110, 160, 330 + i * 110], fill=BLUE)
        d.text((190, 290 + i * 110), ln, font=font(40), fill=FG)
    img.save(f'{OUT}/card_02_problem.png')

    # 3 上游 FAEP
    img, d = base()
    d.text((120, 120), '上游 FAEP：单机自主探索（开源 GPL-3.0）', font=font(56), fill=FG)
    steps = ['深度相机', 'SDF 建图', '前沿检测', 'LKH 巡游', 'B 样条轨迹']
    x = 140
    for i, s in enumerate(steps):
        d.rounded_rectangle = None
        d.rectangle([x, 360, x + 280, 480], fill=(255, 255, 255), outline=BLUE, width=3)
        d.text((x + 140, 420), s, font=font(34), fill=FG, anchor='mm')
        if i < len(steps) - 1:
            d.line([x + 290, 420, x + 340, 420], fill=GREY, width=4)
        x += 355
    d.text((120, 600), '前沿 = 已知与未知的交界；全部前沿消失即探索完成', font=font(34), fill=GREY)
    img.save(f'{OUT}/card_03_faep.png')

    # 4 三机分区
    img, d = base()
    d.text((120, 120), '我们的扩展：三机扇区分工', font=font(60), fill=FG)
    lines = ['按初始位置把地图划成三块（Voronoi 扇区）',
             '任务创建即归属扇区机，不再“最近机抢单”',
             '每机只上报本扇区前沿，全部完成后统一 HALT']
    for i, ln in enumerate(lines):
        d.ellipse([130, 320 + i * 120, 160, 350 + i * 120], fill=GREEN)
        d.text((190, 310 + i * 120), ln, font=font(40), fill=FG)
    d.text((120, 720), '先验证：“有协调器”本身不带来收益——不做分区时协同反而慢 21–29%',
           font=font(30), fill=GREY)
    img.save(f'{OUT}/card_04_coord.png')

    # 5 结果
    img, d = base()
    d.text((120, 110), '结果：三个场景，协同全面反超独立', font=font(56), fill=FG)
    rows = [('单机时间', '66 s', '独立 133 s', '−50%'),
            ('每轮总时长', '74 s', '独立 168 s', '−56%'),
            ('重复覆盖', '7.6%', '独立 94%', '−86pp')]
    for i, (a, b, c, e) in enumerate(rows):
        y = 300 + i * 150
        d.text((140, y), a, font=font(42), fill=GREY)
        d.text((620, y), b, font=font(56), fill=GREEN)
        d.text((980, y + 8), c, font=font(36), fill=GREY)
        d.text((1450, y + 8), e, font=font(40), fill=BLUE)
    d.text((120, 820), 'office2 20×20m；office / office3 同样为 −44~−50%', font=font(32), fill=GREY)
    img.save(f'{OUT}/card_05_result.png')

    # 6 OOM
    img, d = base()
    d.text((120, 110), '可靠性：修掉一个 8–9GB 的隐蔽 OOM', font=font(56), fill=FG)
    lines = ['根因：搜索树父指针链成环 → 路径时长爆炸 → 采样无界增长',
             '四层防御：断环自愈 / 时长上限 / 采样上限 / 调用方健全性检查',
             '结果：内存稳定 1.54GB，批跑零崩溃']
    for i, ln in enumerate(lines):
        d.ellipse([130, 300 + i * 110, 160, 330 + i * 110], fill=(217, 48, 37))
        d.text((190, 290 + i * 110), ln, font=font(38), fill=FG)
    img.save(f'{OUT}/card_06_oom.png')

    # 7 开源
    img, d = base()
    d.text((120, 110), '开源与复现', font=font(60), fill=FG)
    lines = ['代码：GPL-3.0 衍生，保留上游版权声明',
             '数据：三场景 A/B/C 轮次、5Hz 轨迹、原始日志',
             '工具：一键批跑 / 覆盖分析 / 图表与视频生成脚本',
             '复现：README 提供环境、启动、批跑完整命令']
    for i, ln in enumerate(lines):
        d.ellipse([130, 300 + i * 100, 160, 330 + i * 100], fill=GREEN)
        d.text((190, 290 + i * 100), ln, font=font(38), fill=FG)
    img.save(f'{OUT}/card_07_open.png')

    print('cards written to', OUT)


if __name__ == '__main__':
    cards()
