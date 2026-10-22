"""Write DM48X tunings as .mid files: 48 notes in the order
blow holes 1-12, draw 1-12, blow+slider 1-12, draw+slider 1-12 (the firmware's table layout)."""
import math, os, struct, sys
OUT = sys.argv[1]
NAMES = "C Db D Eb E F Gb G Ab A Bb B".split()
def nn(n): return f"{NAMES[n % 12]}{n // 12 - 1}"
def vlq(n):
    out = [n & 127]; n >>= 7
    while n: out.insert(0, (n & 127) | 128); n >>= 7
    return bytes(out)
def write_mid(path, rows, title):
    notes = [n for r in rows for n in r]
    assert len(notes) == 48 and all(0 <= n <= 127 for n in notes), title
    ev = vlq(0) + b"\xff\x03" + vlq(len(title)) + title.encode()
    for n in notes:
        ev += vlq(0 if ev.endswith(title.encode()) else 60) + bytes([0x90, n, 100])
        ev += vlq(60) + bytes([0x80, n, 0])
    ev += vlq(0) + b"\xff\x2f\x00"
    data = b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480) + b"MTrk" + struct.pack(">I", len(ev)) + ev
    open(path, "wb").write(data)
def up(row, k): return [n + k for n in row]
def scale_run(start, steps, n=12):
    out, i, x = [], 0, start
    while len(out) < n:
        out.append(x); x += steps[i % len(steps)]; i += 1
    return out

T = {}
# --- the four low-octave diatonic (Richter) harps, slider = +1 octave
for key, root in (("Bb", 46), ("C", 48), ("D", 50), ("A", 45)):
    blow = [root - 5] + [root + i for i in (0, 4, 7, 12, 16, 19, 24, 28, 31, 36)] + [root + 40]
    draw = [root - 3] + [root + i for i in (2, 7, 11, 14, 17, 21, 23, 26, 29, 33)] + [root + 35]
    T[f"Richter Low {key}"] = [blow, draw, up(blow, 12), up(draw, 12)]
# --- unusual / ambient
harm = lambda h: 24 + round(12 * math.log2(h))   # harmonics of C1
ob = [harm(h) for h in range(2, 14)]
od = [harm(h) for h in range(3, 27, 2)]
T["Ambient - Overtones"] = [ob, od, up(ob, 12), up(od, 12)]
qb = [36 + 5 * i for i in range(12)]
T["Ambient - Quartal Ladder"] = [qb, up(qb, 2), up(qb, 7), up(qb, 9)]
lyd = [0, 2, 4, 6, 7, 9, 11]
lb = scale_run(48, [2, 2, 2, 1, 2, 2, 1])
ld = scale_run(52, [2, 1, 2, 2, 1, 2, 2])          # same Lydian, two scale steps up
T["Ambient - Lydian Clusters"] = [lb, ld, up(lb, 12), up(ld, 12)]
mb = scale_run(48, [2, 2, 2, 3, 1, 2])             # Prometheus / mystic chord on C
md = scale_run(54, [2, 2, 2, 3, 1, 2])             # ... and on F#, a tritone away
T["Ambient - Mystic Tritone"] = [mb, md, up(mb, 12), up(md, 12)]
ib = scale_run(36, [1, 4, 1, 4, 2])                # Iwato on C
idr = scale_run(43, [1, 4, 1, 4, 2])               # Iwato on G
T["Ambient - Iwato Void"] = [ib, idr, up(ib, 12), up(idr, 12)]
iv = [0, 2, 3, 5, 7, 8, 10, 12, 14, 15, 17, 19]
rb = [62 + i for i in iv]                           # D minor rising left to right
rd = [62 - i for i in iv]                           # its mirror image falling
T["Ambient - Mirror"] = [rb, rd, up(rb, 12), up(rd, -12)]
# --- check file: every slot different and easy to read in the Tuning editor
T["Order test"] = [list(range(48, 60)), list(range(60, 72)), list(range(72, 84)), list(range(84, 96))]

os.makedirs(OUT, exist_ok=True)
chart = []
for name, rows in T.items():
    write_mid(os.path.join(OUT, name + ".mid"), rows, name)
    chart.append(f"\n{name}\n" + "\n".join(
        f"  {lbl:<14}" + " ".join(f"{nn(n):>4}" for n in r)
        for lbl, r in zip(("blow", "draw", "blow+slider", "draw+slider"), rows)))
open(os.path.join(OUT, "TUNINGS.txt"), "w").write(
    "Tunings in this folder (holes 1-12, left to right; middle C = C4 = MIDI 60)\n" + "\n".join(chart) + "\n")
print("\n".join(chart))
