"""Generates the bundled original sounds and default puzzle picture.

Run from the project root: python3 tools/make_assets.py
"""
import math
import random
import struct
import wave
from pathlib import Path

import cairo

ROOT = Path(__file__).resolve().parent.parent
SOUNDS = ROOT / "data" / "sounds"
RATE = 44100


def write_wav(path: Path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))


def tone(freq, seconds, attack=0.01, release=0.08, harmonics=(1.0, 0.3, 0.1)):
    n = int(RATE * seconds)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / attack, (seconds - t) / release)
        s = sum(a * math.sin(2 * math.pi * freq * (k + 1) * t) for k, a in enumerate(harmonics))
        out.append(0.5 * env * s / sum(harmonics))
    return out


def pop():
    rng = random.Random(4)
    n = int(RATE * 0.18)
    out = []
    for i in range(n):
        t = i / RATE
        noise = rng.uniform(-1, 1) * math.exp(-t * 40)
        thump = math.sin(2 * math.pi * (180 - 400 * t) * t) * math.exp(-t * 25)
        out.append(0.8 * noise + 0.6 * thump)
    return out


def alarm_tone():
    out = []
    for _ in range(4):
        out += tone(880, 0.12) + [0.0] * int(RATE * 0.06)
        out += tone(1175, 0.12) + [0.0] * int(RATE * 0.06)
    return out + [0.0] * int(RATE * 0.5)


def photo(path: Path, size=900):
    s = cairo.ImageSurface(cairo.FORMAT_RGB24, size, size)
    c = cairo.Context(s)
    c.scale(size / 900, size / 900)
    sky = cairo.LinearGradient(0, 0, 0, 600)
    sky.add_color_stop_rgb(0, 0.33, 0.65, 0.95)
    sky.add_color_stop_rgb(1, 0.75, 0.9, 1.0)
    c.set_source(sky)
    c.paint()
    # rainbow
    for i, col in enumerate([(0.93, 0.2, 0.2), (0.98, 0.55, 0.1), (0.98, 0.85, 0.15),
                             (0.3, 0.75, 0.3), (0.2, 0.45, 0.9), (0.55, 0.3, 0.8)]):
        c.set_source_rgb(*col)
        c.set_line_width(22)
        c.arc(450, 640, 420 - i * 22, math.pi, 2 * math.pi)
        c.stroke()
    # sun with rays
    c.set_source_rgb(1.0, 0.82, 0.1)
    for k in range(12):
        a = k * math.pi / 6
        c.move_to(150 + 70 * math.cos(a), 150 + 70 * math.sin(a))
        c.line_to(150 + 115 * math.cos(a), 150 + 115 * math.sin(a))
    c.set_line_width(12)
    c.stroke()
    c.arc(150, 150, 60, 0, 2 * math.pi)
    c.fill()
    # clouds
    c.set_source_rgb(1, 1, 1)
    for cx, cy in ((690, 130), (560, 260)):
        for dx, dy, r in ((0, 0, 45), (45, -20, 55), (95, 0, 45), (45, 15, 45)):
            c.arc(cx + dx, cy + dy, r, 0, 2 * math.pi)
            c.fill()
    # hills
    c.set_source_rgb(0.35, 0.72, 0.3)
    c.move_to(0, 640)
    c.curve_to(200, 520, 380, 560, 520, 640)
    c.curve_to(650, 560, 800, 540, 900, 600)
    c.line_to(900, 900)
    c.line_to(0, 900)
    c.fill()
    c.set_source_rgb(0.22, 0.58, 0.22)
    c.move_to(0, 760)
    c.curve_to(250, 690, 600, 820, 900, 720)
    c.line_to(900, 900)
    c.line_to(0, 900)
    c.fill()
    # house
    c.set_source_rgb(0.96, 0.4, 0.45)
    c.rectangle(560, 560, 230, 180)
    c.fill()
    c.set_source_rgb(0.45, 0.22, 0.6)
    c.move_to(535, 570)
    c.line_to(675, 450)
    c.line_to(815, 570)
    c.close_path()
    c.fill()
    c.set_source_rgb(0.98, 0.85, 0.3)
    c.rectangle(590, 600, 60, 55)
    c.rectangle(700, 600, 60, 55)
    c.fill()
    c.set_source_rgb(0.45, 0.28, 0.15)
    c.rectangle(650, 660, 50, 80)
    c.fill()
    # tree
    c.set_source_rgb(0.5, 0.3, 0.15)
    c.rectangle(185, 560, 40, 160)
    c.fill()
    c.set_source_rgb(0.1, 0.48, 0.25)
    for dx, dy, r in ((205, 520, 85), (150, 570, 55), (260, 570, 55)):
        c.arc(dx, dy, r, 0, 2 * math.pi)
        c.fill()
    c.set_source_rgb(0.9, 0.15, 0.2)
    for ax, ay in ((170, 500), (240, 540), (200, 590), (150, 560)):
        c.arc(ax, ay, 11, 0, 2 * math.pi)
        c.fill()
    # flowers
    for fx, fy, col in ((80, 820, (1, 0.4, 0.7)), (330, 800, (1, 0.9, 0.2)), (470, 860, (0.6, 0.4, 1)),
                        (820, 830, (1, 0.5, 0.2)), (400, 740, (1, 1, 1))):
        c.set_source_rgb(*col)
        for k in range(5):
            a = k * 2 * math.pi / 5
            c.arc(fx + 16 * math.cos(a), fy + 16 * math.sin(a), 12, 0, 2 * math.pi)
            c.fill()
        c.set_source_rgb(0.95, 0.75, 0.1)
        c.arc(fx, fy, 9, 0, 2 * math.pi)
        c.fill()
    s.write_to_png(str(path))


def main():
    SOUNDS.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate((330.0, 440.0, 554.4, 659.3)):
        write_wav(SOUNDS / f"simon-{i}.wav", tone(f, 0.45))
    write_wav(SOUNDS / "pop.wav", pop())
    write_wav(SOUNDS / "alarm-tone.wav", alarm_tone())
    photo(ROOT / "data" / "default-puzzle.png")


if __name__ == "__main__":
    main()
