#!/usr/bin/env python3
"""把 Edge TTS 生成的 SRT 转成适合 1080p 视频烧录的 ASS 字幕。"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)
PUNCT_RE = re.compile(r"[^，。；：！？]+[，。；：！？]?")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[._:/+-][A-Za-z0-9]+)*|.", re.DOTALL)


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, milliseconds = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def format_time(value: float) -> str:
    value = max(0.0, value)
    hours = int(value // 3600)
    minutes = int(value % 3600 // 60)
    seconds = value % 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def wrap_text(text: str, max_chars: int = 30) -> str:
    text = "".join(text.split())
    chunks = [chunk.strip() for chunk in PUNCT_RE.findall(text) if chunk.strip()]
    if not chunks:
        chunks = [text]

    def split_long_clause(clause: str) -> list[str]:
        """按字符宽度换行，同时避免把 FAEP 等拉丁词拆开。"""
        tokens = TOKEN_RE.findall(clause)
        parts: list[str] = []
        current_part = ""
        for token in tokens:
            if current_part and len(current_part) + len(token) > max_chars:
                parts.append(current_part)
                current_part = token
            else:
                current_part += token
        if current_part:
            parts.append(current_part)
        return parts or [clause]

    lines: list[str] = []
    current = ""
    for chunk in chunks:
        while len(chunk) > max_chars:
            if current:
                lines.append(current)
                current = ""
            parts = split_long_clause(chunk)
            lines.extend(parts[:-1])
            chunk = parts[-1]
        if len(current) + len(chunk) <= max_chars:
            current += chunk
        else:
            if current:
                lines.append(current)
            current = chunk
    if current:
        lines.append(current)

    # 合并过短的尾行，避免“十九。”或“十。”被单独拆出。
    if len(lines) > 1 and len(lines[-1].strip()) <= 3:
        lines[-2] += lines[-1].strip()
        lines.pop()

    if len(lines) > 2:
        lines = [lines[0], "".join(lines[1:])]
    return r"\N".join(lines)


def read_srt(path: Path) -> list[tuple[float, float, str]]:
    blocks = re.split(r"\r?\n\r?\n", path.read_text(encoding="utf-8-sig").strip())
    cues: list[tuple[float, float, str]] = []
    for block in blocks:
        lines = block.splitlines()
        time_index = next((index for index, line in enumerate(lines) if "-->" in line), None)
        if time_index is None:
            continue
        match = TIME_RE.search(lines[time_index])
        if not match:
            continue
        text = " ".join(lines[time_index + 1 :]).strip()
        cues.append(
            (
                parse_time(match.group("start")),
                parse_time(match.group("end")),
                text,
            )
        )
    return cues


def write_ass(cues: list[tuple[float, float, str]], output: Path) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Subtitle,Noto Sans CJK SC,30,&H00FFFFFF,&H000000FF,&H00101824,&H70000000,-1,0,0,0,100,100,1,0,1,3,1,2,90,90,12,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    rows: list[str] = []
    previous_end = 0.0
    for index, (start, end, text) in enumerate(cues):
        start = max(start, previous_end + 0.01)
        if index + 1 < len(cues):
            end = min(end, cues[index + 1][0] - 0.01)
        if end <= start:
            continue
        previous_end = end
        wrapped = wrap_text(text)
        rows.append(
            "Dialogue: 0,"
            f"{format_time(start)},{format_time(end)},Subtitle,,0,0,0,,"
            r"{\fad(120,120)}"
            f"{wrapped}"
        )
    output.write_text(header + "\n".join(rows) + "\n", encoding="utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_ass(read_srt(args.input), args.output)


if __name__ == "__main__":
    main()
