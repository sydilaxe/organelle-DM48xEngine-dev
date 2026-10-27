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
# --- diatonic (Richter-style) harps: the 10 classic holes plus an extra low hole 1 and high hole 12; slider = +1 octave
RB = [-5, 0, 4, 7, 12, 16, 19, 24, 28, 31, 36, 40]      # blow, relative to the key
RD = [-3, 2, 7, 11, 14, 17, 21, 23, 26, 29, 33, 35]     # draw
def harp(root, blow=RB, draw=RD, bmod=None, dmod=None):
    b = [root + i for i in blow]; d = [root + i for i in draw]
    for h, k in (bmod or {}).items(): b[h] += k          # h = classic hole number (index 1..10)
    for h, k in (dmod or {}).items(): d[h] += k
    return [b, d, up(b, 12), up(d, 12)]
KEYS = {"G": 43, "Ab": 44, "A": 45, "Bb": 46, "B": 47, "C": 48, "Db": 49, "D": 50, "Eb": 51, "E": 52, "F": 53, "F#": 54}
for key in KEYS:   # all 12 keys, key note between G2 and F#3
    T[f"Richter/Richter Low {key}"] = harp(KEYS[key])
# Country: draw 5 a semitone up (major 7th in 2nd position)
for key in ("C", "G", "A", "D"):
    T[f"Richter/Country {key}"] = harp(KEYS[key], dmod={5: 1})
# Paddy Richter: blow 3 a whole step up (fiddle tunes, full scale in the low octave)
for key in ("C", "G", "D"):
    T[f"Richter/Paddy Richter {key}"] = harp(KEYS[key], bmod={3: 2})
# Harmonic minor: minor blow chord, draw with flat 6
HB = [-5, 0, 3, 7, 12, 15, 19, 24, 27, 31, 36, 39]
HD = [-4, 2, 7, 11, 14, 17, 20, 23, 26, 29, 32, 35]
for key in ("A", "C", "D", "E"):
    T[f"Richter/Harmonic Minor {key}"] = harp(KEYS[key], HB, HD)

# --- chromatic layouts: the slider raises a semitone, like a chromatic harmonica, so all 12 notes are playable
def chrom(blow, draw):
    return [blow, draw, up(blow, 1), up(draw, 1)]
def solo(root):   # solo tuning: blow C E G C, draw D F A B, three octaves
    return chrom([root + 12 * o + i for o in range(3) for i in (0, 4, 7, 12)],
                 [root + 12 * o + i for o in range(3) for i in (2, 5, 9, 11)])
T["Chromatic/Solo C"] = solo(48)
T["Chromatic/Solo G"] = solo(43)
T["Chromatic/Low C"] = solo(36)
T["Chromatic/Augmented"] = chrom([48 + 4 * i for i in range(12)], [50 + 4 * i for i in range(12)])   # whole-tone pairs
T["Chromatic/Diminished"] = chrom([48 + 3 * i for i in range(12)], [50 + 3 * i for i in range(12)])  # minor-third stacks

# --- unusual / ambient
harm = lambda h: 24 + round(12 * math.log2(h))   # harmonics of C1
ob = [harm(h) for h in range(2, 14)]
od = [harm(h) for h in range(3, 27, 2)]
T["Ambient/Overtones"] = [ob, od, up(ob, 12), up(od, 12)]
qb = [36 + 5 * i for i in range(12)]
T["Ambient/Quartal Ladder"] = [qb, up(qb, 2), up(qb, 7), up(qb, 9)]
lyd = [0, 2, 4, 6, 7, 9, 11]
lb = scale_run(48, [2, 2, 2, 1, 2, 2, 1])
ld = scale_run(52, [2, 1, 2, 2, 1, 2, 2])          # same Lydian, two scale steps up
T["Ambient/Lydian Clusters"] = [lb, ld, up(lb, 12), up(ld, 12)]
mb = scale_run(48, [2, 2, 2, 3, 1, 2])             # Prometheus / mystic chord on C
md = scale_run(54, [2, 2, 2, 3, 1, 2])             # ... and on F#, a tritone away
T["Ambient/Mystic Tritone"] = [mb, md, up(mb, 12), up(md, 12)]
ib = scale_run(36, [1, 4, 1, 4, 2])                # Iwato on C
idr = scale_run(43, [1, 4, 1, 4, 2])               # Iwato on G
T["Ambient/Iwato Void"] = [ib, idr, up(ib, 12), up(idr, 12)]
iv = [0, 2, 3, 5, 7, 8, 10, 12, 14, 15, 17, 19]
rb = [62 + i for i in iv]                           # D minor rising left to right
rd = [62 - i for i in iv]                           # its mirror image falling
T["Ambient/Mirror"] = [rb, rd, up(rb, 12), up(rd, -12)]
fb = scale_run(36, [2, 2, 3, 2, 3])                # C major pentatonic from C2 ...
fd = up(fb, 7)                                     # ... and each draw a fifth above its blow: open fifths
T["Ambient/Open Fifths"] = [fb, fd, up(fb, 12), up(fd, 12)]
tb = scale_run(50, [3, 4, 3, 4, 3, 4, 3])          # D Dorian in thirds: three adjacent holes = a 7th chord
td = scale_run(52, [3, 4, 3, 3, 4, 3, 4])          # the same, one scale step up
T["Ambient/Dorian Thirds"] = [tb, td, up(tb, -12), up(td, -12)]
pb = scale_run(48, [2, 2, 3, 2, 3])                # C major pentatonic
pd = scale_run(57, [3, 2, 2, 3, 2])                # A minor pentatonic (same notes, offset)
T["Ambient/Pentatonic Rain"] = [pb, pd, up(pb, 12), up(pd, 12)]
hb = scale_run(48, [1, 3])                         # augmented hexatonic, dreamy and symmetric
hd = scale_run(52, [3, 1])
T["Ambient/Hexatonic Glass"] = [hb, hd, up(hb, 12), up(hd, 12)]
# --- world scales: blow and draw walk the scale (draw one step above blow); slider = +1 octave.
# The name ends in the key, so sending also sets the synth's Key: pick the matching scale on the TUNE page for the true pitches.
def walk(root, steps):
    b = scale_run(root, steps)
    d = scale_run(root + steps[0], steps[1:] + steps[:1])
    return [b, d, up(b, 12), up(d, 12)]
T["World/Hijaz D"] = walk(50, [1, 3, 1, 2, 1, 2, 2])
T["World/Raga Bhairav C"] = walk(48, [1, 3, 1, 2, 1, 3, 1])
T["World/Hungarian Minor A"] = walk(45, [2, 1, 3, 1, 1, 3, 1])
T["World/Hirajoshi E"] = walk(40, [2, 1, 4, 1, 4])
T["World/Pelog C"] = walk(48, [1, 2, 4, 1, 4])
T["World/Slendro C"] = walk(48, [2, 3, 2, 2, 3])
T["World/Double Harmonic E"] = walk(40, [1, 3, 1, 2, 1, 3, 1])
# --- check file: every slot different and easy to read in the Tuning editor
T["Order test"] = [list(range(48, 60)), list(range(60, 72)), list(range(72, 84)), list(range(84, 96))]

os.makedirs(OUT, exist_ok=True)
chart = []
for name, rows in T.items():          # "Folder/Name": the LIBRARY page's knob 2 picks the folder
    path = os.path.join(OUT, name + ".mid")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_mid(path, rows, name.split("/")[-1])
    chart.append(f"\n{name.replace('/', ' / ')}\n" + "\n".join(
        f"  {lbl:<14}" + " ".join(f"{nn(n):>4}" for n in r)
        for lbl, r in zip(("blow", "draw", "blow+slider", "draw+slider"), rows)))
open(os.path.join(OUT, "TUNINGS.txt"), "w").write(
    "Tunings in this folder and its subfolders (holes 1-12, left to right; middle C = C4 = MIDI 60)\n" + "\n".join(chart) + "\n")
print("\n".join(chart))
