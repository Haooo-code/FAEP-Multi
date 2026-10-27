#!/usr/bin/env python3
"""边缘区域优先（min_dis_edge）行为级证据分析

输入：frontier_finder 决策日志（EVAL/F/TOUR 三种行）
输出：
  1) 控制台统计（挑选目标 vs 全部前沿的贴边度对比、同巡游内排名、小区域触发统计）
  2) 反事实重解：把 edge_term 置零、其余项不变，用 LKH 重解 ATSP，对比首选前沿是否变化
  3) 数据集：edge_resample.csv（供 LKH 反事实使用）+ 若干 PNG 图（若 matplotlib 可用）
"""
import argparse
import math
import os
import re
import statistics as st
import subprocess
import sys

EDGE_THRESH = 4.0     # 代码里"贴边"启发式阈值（min_x<4 或 min_y<4）
LKH_BIN = '/tmp/lkh_wrap'   # 用 FAEP 的 liblkh 编译的小包装（接受 par 文件参数）
TMP = '/tmp/edge_ablation'
CJK_FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
CJK_FALLBACK = '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'


def setup_matplotlib_font():
    """让 matplotlib 支持中文（WSL 自带 Droid Sans Fallback）"""
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import font_manager as fm
    matplotlib.rcParams['font.family'] = ['sans-serif']
    matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Droid Sans Fallback', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
    if os.path.exists(CJK_FONT):
        try:
            if hasattr(fm.fontManager, 'addfont'):
                fm.fontManager.addfont(CJK_FONT)
            elif not any(getattr(f, 'fname', '') == CJK_FONT for f in fm.fontManager.ttflist):
                # matplotlib 3.1（Ubuntu 20.04）：手动登记字体（ttc 取第一个字面）
                fm.fontManager.ttflist.append(fm.FontEntry(
                    fname=CJK_FONT, name='Noto Sans CJK SC', style='normal',
                    variant='normal', weight='normal', stretch='normal', size='scalable'))
        except Exception as e:
            print(f'中文字体注册失败（{e}），图内文字可能缺字')

RE_EVAL = re.compile(
    r'EVAL t=(?P<t>[\d.]+) cur=([-\d.]+),([-\d.]+),([-\d.]+) n=(?P<n>\d+) '
    r'xb=\(([-\d.]+),([-\d.]+)\) yb=\(([-\d.]+),([-\d.]+)\) edge_scale=(?P<scale>[\d.]+)')
RE_F = re.compile(
    r'F idx=(?P<idx>\d+) dist=(?P<dist>[\d.eE+-]+) minx=([-\d.eE+]+) miny=([-\d.eE+]+) '
    r'edge=(?P<edge>[-\d.eE+]+) edge_term=(?P<eterm>[-\d.eE+]+) ang=([-\d.eE+]+) '
    r'pi=(?P<pi>[\d.eE+-]+) pp=(?P<pp>[\d.eE+-]+) small=(?P<small>\d) trig=(?P<trig>\d) '
    r'sma_z=([-\d.eE+]+) cost=(?P<cost>[-\d.eE+]+)')
RE_TOUR = re.compile(r'TOUR t=(?P<t>[\d.]+) first_idx=(?P<first>\S+) tour=(?P<tour>[\d,]*)')
RE_FLIGHT = re.compile(r'\[(?:INFO|WARN)\] \[([\d.]+)\]: Flight_time\]: ([\d.]+)')


def parse(path):
    evals = []          # 每次巡游规划：{t, cur, n, rows:[{...}], first}
    cur_ev = None
    for line in open(path, errors='replace'):
        line = line.rstrip('\n')
        m = RE_EVAL.match(line)
        if m:
            cur_ev = dict(t=float(m['t']), cur=(float(m.group(2)), float(m.group(3)), float(m.group(4))),
                          n=int(m['n']), scale=float(m['scale']), rows=[], first=None, tour=None)
            evals.append(cur_ev)
            continue
        m = RE_F.match(line)
        if m and cur_ev is not None:
            cur_ev['rows'].append(dict(
                idx=int(m['idx']), dist=float(m['dist']), edge=float(m['edge']),
                eterm=float(m['eterm']), pi=float(m['pi']), pp=float(m['pp']),
                small=int(m['small']), trig=int(m['trig']), cost=float(m['cost'])))
            continue
        m = RE_TOUR.match(line)
        if m and cur_ev is not None:
            cur_ev['first'] = None if m['first'] == 'NA' else int(m['first'])
            cur_ev['tour'] = [int(x) for x in m['tour'].split(',') if x] if m['tour'] else []
            continue
    return evals


def quantile_rank(values, v):
    """v 在 values 中从小到大的分位（0=最小）"""
    less = sum(1 for x in values if x < v - 1e-12)
    return less / max(1, len(values))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', default='/mnt/d/WSL/edge_debug_main.log')
    ap.add_argument('--outdir', default='/mnt/d/WSL/edge_analysis')
    ap.add_argument('--ablation', action='store_true', help='启用 LKH 反事实重解')
    ap.add_argument('--video', action='store_true', help='生成机理录屏视频（叠加证据面板）')
    ap.add_argument('--frames', default='/mnt/d/WSL/rec_frames')
    ap.add_argument('--simlog', default='/mnt/d/WSL/sim_rec.log')
    ap.add_argument('--caplog', default='', help='抓帧日志（用于取实测帧率；默认按 --frames 的 tag 推）')
    ap.add_argument('--t0', default='', help='首帧对应的 epoch 秒（抓帧起始时刻，覆盖默认锚点）')
    ap.add_argument('--compare', default='', help='边缘项消融对照日志（edge_priority_scale=0 那一轮）')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    evals = parse(args.log)
    print(f'解析到 {len(evals)} 次全局巡游规划（EVAL）')
    with_rows = [e for e in evals if e['rows'] and e['first'] is not None]
    print(f'其中 {len(with_rows)} 次有完整前沿明细 + 选择结果')

    # ---- 1) 选择目标 vs 全体前沿 的贴边度对比 ----
    chosen_edges, chosen_ranks, interior_all, edge_all = [], [], [], []
    chosen_edgecnt, interior_cnt = 0, 0
    for e in with_rows:
        edges = [r['edge'] for r in e['rows']]
        first = e['first']
        if first < 0 or first >= len(e['rows']):
            continue
        ce = e['rows'][first]['edge']
        chosen_edges.append(ce)
        chosen_ranks.append(quantile_rank(edges, ce))
        if ce < EDGE_THRESH:
            chosen_edgecnt += 1
            edge_all.append(ce)
        else:
            interior_cnt += 1
            interior_all.append(ce)
        if e['rows'][first]['trig']:
            pass

    def fmt(v):
        return f'{st.mean(v):.3f} ± {st.pstdev(v):.3f} (n={len(v)})' if v else 'N/A'

    print('\n==== 选择目标的前沿贴边度 ====')
    print(f'被选为下一个执行目标的 min_dis_edge：{fmt(chosen_edges)}')
    print(f'  其中贴边(<{EDGE_THRESH}m) 占比：{chosen_edgecnt}/{chosen_edgecnt+interior_cnt} = '
          f'{chosen_edgecnt / max(1, chosen_edgecnt + interior_cnt):.1%}')
    print(f'同巡游内排名分位（0=最贴边）：{fmt(chosen_ranks)}')

    # 全体前沿的基线占比
    tot_e, tot_all = 0, 0
    for e in with_rows:
        for r in e['rows']:
            tot_all += 1
            if r['edge'] < EDGE_THRESH:
                tot_e += 1
    print(f'全体候选前沿中贴边占比（基线）：{tot_e}/{tot_all} = {tot_e / max(1, tot_all):.1%}')

    # ---- 小区域机制统计 ----
    trig_total = sum(r['trig'] for e in evals for r in e['rows'])
    trig_evals = [e for e in evals if any(r['trig'] for r in e['rows'])]
    ev_after_trig = 0
    trig_eval_ts = {e['t'] for e in trig_evals}
    trig_list = sorted(e['t'] for e in trig_evals)
    for e in with_rows:
        if any(abs(e['t'] - tt) <= 12.0 for tt in trig_list) and e['rows'][e['first']]['trig']:
            ev_after_trig += 1
    print('\n==== 小区域优先机制 ====')
    print(f'触发小区域判定的前沿-巡游组合数：{trig_total}')
    print(f'涉及巡游次数：{len(trig_evals)} / {len(evals)}')
    first_trig = sum(1 for e in with_rows if e['rows'][e['first']]['trig'])
    print(f'其中"被直接选为下一个目标"的次数：{first_trig}')

    # ---- 2) 数据导出 + LKH 反事实 ----
    csv_path = os.path.join(args.outdir, 'edge_resample.csv')
    with open(csv_path, 'w') as f:
        f.write('eval,t,n,scale,first_idx,first_edge,first_eterm,first_cost,all_edges,all_eterms,all_costs\n')
        for k, e in enumerate(with_rows):
            f.write(','.join([
                str(k), f"{e['t']:.3f}", str(e['n']), f"{e['scale']:.3f}",
                str(e['first']), f"{e['rows'][e['first']]['edge']:.4f}",
                f"{e['rows'][e['first']]['eterm']:.4f}", f"{e['rows'][e['first']]['cost']:.4f}",
                ';'.join(f"{r['edge']:.4f}" for r in e['rows']),
                ';'.join(f"{r['eterm']:.4f}" for r in e['rows']),
                ';'.join(f"{r['cost']:.4f}" for r in e['rows']),
            ]) + '\n')
    print(f'\n写出数据集：{csv_path}')

    if args.ablation and os.path.exists(LKH_BIN):
        os.makedirs(TMP, exist_ok=True)
        # LKH 不接受负权：全局统一平移（原 flyCost 可低至 -110 量级）
        gmin = min((r['cost'] - r['eterm'] for e in with_rows for r in e['rows']), default=0.0)
        gmin = min(gmin, min((r['cost'] for e in with_rows for r in e['rows']), default=0.0))
        offset = -gmin + 10.0
        changed, cnt, fail, repro = 0, 0, 0, 0
        for k, e in enumerate(with_rows):
            n = len(e['rows'])
            base_cost = [r['cost'] for r in e['rows']]
            eterm = [r['eterm'] for r in e['rows']]
            cf_cost = [c - t for c, t in zip(base_cost, eterm)]  # 关闭边缘项（含缩放）
            pick_base = lkh_solve(k, n, base_cost, 'base', offset)
            pick_cf = lkh_solve(k, n, cf_cost, 'cf', offset)
            if pick_base is None or pick_cf is None:
                fail += 1
                continue
            cnt += 1
            # 与日志中的真实选择核对（应一致，验证重解正确性）
            if pick_base == e['first']:
                repro += 1
            if pick_base != pick_cf:
                changed += 1
        print('\n==== 反事实重解（edge_term 置零）====')
        print(f'可对比巡游：{cnt}（失败 {fail}）')
        print(f'重解首选与日志记录一致：{repro}/{cnt}（{repro / max(1, cnt):.1%}，验证重解管线可信）')
        print(f'首选前沿发生变化：{changed} 次（{changed / max(1, cnt):.1%}）')

    # ---- 3) 图表（可选）----
    try:
        setup_matplotlib_font()
        import matplotlib.pyplot as plt

        ts = [e['t'] - with_rows[0]['t'] for e in with_rows]
        fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
        ax = axes[0]
        for e, t in zip(with_rows, ts):
            avg = st.mean([r['edge'] for r in e['rows']])
            ax.plot(t, avg, '.', color='#9aa0a6', ms=3, label='巡游内平均' if t == ts[0] else None)
        ax.plot(ts, [e['rows'][e['first']]['edge'] for e in with_rows], 'o-', color='#1a73e8',
                ms=4, lw=1.0, label='实际选择的下一个目标')
        ax.axhline(EDGE_THRESH, color='#e8710a', ls='--', lw=1, label=f'贴边阈值 {EDGE_THRESH:g}m')
        ax.set_ylabel('到边界的距离 min_dis_edge (m)')
        ax.set_title('边缘区域优先：实际选择目标始终贴近边界（office 场景单机一轮）')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(alpha=0.3)

        ax = axes[1]
        trig_ts = [tt - with_rows[0]['t'] for tt in trig_list]
        ax.plot(trig_ts, [1] * len(trig_ts), '|', color='#d93025', ms=12,
                label=f'小区域机制触发（{trig_total} 次前沿判定）')
        ax.plot(ts, [e['rows'][e['first']]['trig'] for e in with_rows], 'x', color='#188038',
                label='被选为目标且本次触发小区域机制')
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['', '事件'])
        ax.set_xlabel('时间 (s)')
        ax.legend(loc='upper right', fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig_path = os.path.join(args.outdir, 'edge_priority_timeline.png')
        fig.savefig(fig_path, dpi=150)
        print(f'图已保存：{fig_path}')
    except Exception as ex:
        print(f'绘图跳过（{ex}）')

    if args.video:
        make_video(args, evals, with_rows)

    if args.compare:
        compare_runs(args, with_rows, args.compare)


def lkh_solve(tag, n, fly_costs, suffix, offset):
    """按 FAEP 的 ATSP 结构（行 0=到各前沿的代价，其余=0）调用 LKH 求解，返回路径第 1 个节点下标。

    注意：LKH 对负权值会段错误，因此把所有代价统一平移 +offset（不改变最优巡游）。
    """
    dim = n + 1
    lines = [f'NAME : edge_{tag}_{suffix}', 'TYPE : ATSP', f'DIMENSION : {dim}',
             'EDGE_WEIGHT_TYPE : EXPLICIT', 'EDGE_WEIGHT_FORMAT : FULL_MATRIX',
             'EDGE_WEIGHT_SECTION']
    scale = 100
    big = 10 ** 6   # LKH 对显式矩阵权重有上限（INT_MAX/2/PRECISION），取安全值
    row0 = ['0'] + [str(int(round((c + offset) * scale))) for c in fly_costs]
    lines.append(' '.join(row0))
    for _ in range(n):
        r = ['0'] * dim
        r[1] = str(big)   # 回到当前状态的动作不允许（避免零代价入边）
        lines.append(' '.join(r))
    lines.append('EOF')
    tsp = f'{TMP}/s{suffix}.tsp'
    par = f'{TMP}/s{suffix}.par'
    txt = f'{TMP}/s{suffix}.txt'
    open(tsp, 'w').write('\n'.join(lines) + '\n')
    open(par, 'w').write(
        f'PROBLEM_FILE = {tsp}\nOUTPUT_TOUR_FILE = {txt}\nRUNS = 1\n')
    try:
        subprocess.run([LKH_BIN, par], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=30)
        seq = []
        started = False
        for ln in open(txt):
            ln = ln.strip()
            if ln == 'TOUR_SECTION':
                started = True
                continue
            if not started:
                continue
            if ln in ('-1', 'EOF', ''):
                break
            seq.append(int(ln))
        seq2 = [x for x in seq if x != 1]
        return seq2[0] - 2 if seq2 else None
    except Exception:
        return None


def detect_frame_timing(frames_dir, cap_log='/tmp/cap_loop_main.log'):
    """返回 (帧数, 平均间隔秒)。优先读抓帧日志里的实测值。"""
    n = len([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    if n == 0:
        return 0, 0.4
    try:
        txt = open(cap_log).read()
        m = re.search(r'CAPTURED(?:_XWD)? (\d+) frames in ([\d.]+)s', txt)
        if m and int(m.group(1)) == n:
            return n, float(m.group(2)) / n
    except Exception:
        pass
    return n, 0.4


def parse_flight_interval(simlog):
    """从 sim 日志里取 Flight_time 的发布时刻（ros::Time::now() 秒）"""
    t0 = t1 = None
    try:
        for line in open(simlog, errors='replace'):
            m = RE_FLIGHT.search(line)
            if m:
                stamp = float(m.group(1))
                if t0 is None:
                    t0 = stamp
                t1 = stamp
    except Exception:
        pass
    return t0, t1


def render_panel(ctx_lines, width, cjk=True):
    """渲染证据面板（PIL）"""
    from PIL import Image, ImageDraw, ImageFont
    font = None
    if cjk and os.path.exists(CJK_FONT):
        try:
            font = ImageFont.truetype(CJK_FONT, 23)
        except Exception:
            font = None
    if font is None:
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 22)
        except Exception:
            font = ImageFont.load_default()
    line_h = (font.getbbox('Ag')[3] - font.getbbox('Ag')[1]) + 12 if hasattr(font, 'getbbox') else 34
    pad = 14
    panel_w = max(360, width - 24)
    panel_h = pad * 2 + line_h * len(ctx_lines)
    panel = Image.new('RGBA', (panel_w, panel_h), (16, 18, 24, 215))
    dr = ImageDraw.Draw(panel)
    y = pad
    for i, ln in enumerate(ctx_lines):
        color = (255, 255, 255, 255)
        if ln.startswith('★'):
            color = (255, 196, 0, 255)
        elif ln.startswith('▸'):
            color = (120, 220, 255, 255)
        dr.text((pad, y), ln, font=font, fill=color)
        y += line_h
    return panel


VIDEO_W = 1280


def run_summary(with_rows):
    """一组数据的核心指标：选择目标的贴边度分布"""
    chosen, ranks, edge_cnt = [], [], 0
    tot_e, tot_all = 0, 0
    for e in with_rows:
        edges = [r['edge'] for r in e['rows']]
        f = e['first']
        if not (0 <= f < len(e['rows'])):
            continue
        ce = e['rows'][f]['edge']
        chosen.append(ce)
        ranks.append(quantile_rank(edges, ce))
        if ce < EDGE_THRESH:
            edge_cnt += 1
        for r in e['rows']:
            tot_all += 1
            if r['edge'] < EDGE_THRESH:
                tot_e += 1
    return dict(n=len(chosen), edge_cnt=edge_cnt,
                edge_frac=edge_cnt / max(1, len(chosen)),
                mean_edge=st.mean(chosen) if chosen else float('nan'),
                mean_rank=st.mean(ranks) if ranks else float('nan'),
                base_frac=tot_e / max(1, tot_all))


def compare_runs(args, rows_main, path_ablate):
    """消融对照：正常轮 vs edge_priority_scale=0 轮"""
    if not os.path.exists(path_ablate):
        print(f'对照日志不存在：{path_ablate}')
        return
    ev_ab = [e for e in parse(path_ablate) if e['rows'] and e['first'] is not None]
    if not ev_ab:
        print('对照日志无有效巡游')
        return
    a = run_summary(rows_main)
    b = run_summary(ev_ab)
    print('\n==== 边缘优先消融对照 ====')
    print(f'{"指标":<28}{"正常轮(scale=1)":>18}{"消融轮(scale=0)":>18}')
    print(f'{"巡游次数":<28}{a["n"]:>18}{b["n"]:>18}')
    print(f'{"选择目标贴边(<4m)占比":<26}{a["edge_frac"]:>17.1%}{b["edge_frac"]:>18.1%}')
    print(f'{"选择目标平均贴边距离(m)":<25}{a["mean_edge"]:>18.2f}{b["mean_edge"]:>18.2f}')
    print(f'{"选择目标平均贴边排名(0=最贴边)":<23}{a["mean_rank"]:>17.3f}{b["mean_rank"]:>18.3f}')
    print(f'{"候选前沿基线贴边占比":<25}{a["base_frac"]:>18.1%}{b["base_frac"]:>18.1%}')

    try:
        setup_matplotlib_font()
        import matplotlib.pyplot as plt
        rng = (0, 0)
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
        for ax, s, title in zip(axes, (a, b),
                                ('正常轮（edge_priority_scale=1）',
                                 '消融轮（edge_priority_scale=0）')):
            bars = [s['edge_frac'], s['base_frac']]
            ax.bar(['选择目标', '候选基线'], bars,
                   color=['#1a73e8', '#9aa0a6'])
            for i, v in enumerate(bars):
                ax.text(i, v + 0.02, f'{v:.1%}', ha='center', fontsize=11)
            ax.set_ylim(0, 1.05)
            ax.set_title(title)
            ax.set_ylabel('贴边(<4m)占比')
            ax.grid(alpha=0.3, axis='y')
        fig.suptitle('边缘区域优先机制：消融对照（office 场景 · 单机）', fontsize=13, y=1.02)
        fig.tight_layout()
        p = os.path.join(args.outdir, 'edge_ablation_compare.png')
        fig.savefig(p, dpi=150)
        print(f'对照图已保存：{p}')
    except Exception as ex:
        print(f'对照绘图跳过（{ex}）')


def make_video(args, evals, with_rows):
    """用抓帧 + 决策日志合成带证据面板的机理录屏"""
    from PIL import Image

    frames = sorted(f for f in os.listdir(args.frames) if f.endswith('.png'))
    if not frames:
        print('没有抓帧数据，跳过视频生成')
        return
    caplog = args.caplog or ('/tmp/cap_loop_' + os.path.basename(args.frames).replace('rec_frames_', '') + '.log')
    n, dt = detect_frame_timing(args.frames, caplog)

    evals_all = [e for e in evals if e['rows']]
    if not evals_all:
        print('决策日志为空，跳过视频生成')
        return

    # 抓帧起始时间锚点：优先用 --t0（录制脚本记录的真实起始时刻），否则以第一个 EVAL 回退 5s
    t_frame0 = float(args.t0) if args.t0 else evals_all[0]['t'] - 5.0

    # 逐次巡游：累计触发数 + 实际选择 + "关闭边缘项"的对照选择（离线重算）
    calls = []
    cum = 0
    for e in evals_all:
        cum += sum(r['trig'] for r in e['rows'])
        if e['first'] is None or not (0 <= e['first'] < len(e['rows'])):
            continue
        ce = e['rows'][e['first']]
        base = [r['cost'] - r['eterm'] for r in e['rows']]
        cf_idx = min(range(len(base)), key=lambda i: base[i])
        calls.append(dict(t=e['t'], cum=cum, chosen=ce, cf_idx=cf_idx,
                          cf_row=e['rows'][cf_idx], n=len(e['rows']), cur=e['cur']))
    call_ts = [c['t'] for c in calls]
    import bisect

    img0 = Image.open(os.path.join(args.frames, frames[0])).convert('RGB')
    vw, vh = VIDEO_W, int(round(img0.size[1] * VIDEO_W / img0.size[0] / 2) * 2)

    out_path = os.path.join(args.outdir, 'small_area_mechanism.mp4')
    ff = subprocess.Popen([
        'ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
        '-s', f'{vw}x{vh}', '-r', f'{1.0 / dt:.4f}', '-i', '-',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        out_path], stdin=subprocess.PIPE)

    panel_cache, panel_key = None, None
    differ_cnt = 0
    for i, fname in enumerate(frames):
        t_wall = t_frame0 + i * dt
        img = Image.open(os.path.join(args.frames, fname)).convert('RGB')
        if img.size != (vw, vh):
            img = img.resize((vw, vh), Image.LANCZOS)
        k = bisect.bisect_right(call_ts, t_wall) - 1
        c = calls[k] if k >= 0 else None
        if c is not None and c['cf_row'] is not c['chosen']:
            differ_cnt += 1
        if panel_key != k:
            if c is None:
                lines = ['[小区域优先机制] 现场录屏（office 场景 / 单机 FAEP）',
                         '等待探索开始 ...']
            else:
                ce, cf = c['chosen'], c['cf_row']
                t_off = c['t'] - t_frame0
                lines = [
                    f'[小区域优先机制] 现场录屏（office / 单机）   t = {t_off:6.1f} s',
                    f'小区域事件累计触发 {c["cum"]} 次 | 本次候选前沿 {c["n"]} 个',
                    f'无人机位置 ({c["cur"][0]:6.1f}, {c["cur"][1]:6.1f}) m',
                ]
                lines.append('实际选择  ：贴边距离 {edge:6.1f} m  小区域奖励 {bonus:6.1f}  边缘项 {eterm:6.1f}  代价 {cost:6.1f}'
                             .format(edge=ce['edge'], bonus=-(5 - ce['pi']) * ce['pp'],
                                     eterm=ce['eterm'], cost=ce['cost']))
                lines.append('对照选择* ：贴边距离 {edge:6.1f} m  小区域奖励 {bonus:6.1f}  边缘项 {eterm:6.1f}  代价 {cost:6.1f}'
                             .format(edge=cf['edge'], bonus=-(5 - cf['pi']) * cf['pp'],
                                     eterm=cf['eterm'], cost=cf['cost']))
                lines.append('* 对照 = 关闭边缘优先项后的同一代价函数重新排序')
                if cf is not ce:
                    lines.append('★ 本次两方案选择不同 —— 边缘优先项改变了探索目标')
                else:
                    lines.append('本次两方案选择一致')
            panel_cache = render_panel(lines, vw)
            panel_key = k
        img.paste(panel_cache, (12, 12), panel_cache)
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    print(f'视频已生成：{out_path}（{n} 帧，平均间隔 {dt:.3f}s，'
          f'其中 {differ_cnt} 帧显示"两方案选择不同"）')


if __name__ == '__main__':
    main()
