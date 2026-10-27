"""Automated checks for DM48 Engine (used by the release workflow).

Runs the patch offline in Pure Data (pd -batch) with scripted input and asserts on the results.
Usage:  python3 ci_check.py "../DM48 Engine"      exit code 0 = all checks passed
"""
import os
import subprocess
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import run, audio, f0  # noqa: E402

P = sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"
SR = 44100
ENGINES = ["halo", "lyra", "steel", "under", "velvet", "volt"]
failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok:
        failures.append(name)


def errors(log):
    return [l for l in log.splitlines() if "error" in l.lower() or "couldn't create" in l]


def rms(x, a, b):
    s = x[int(a * SR):int(b * SR)]
    return float(np.sqrt((s ** 2).mean())) if len(s) else 0.0


def key(ev, t, n, hold=60):
    ev += [(t, f"notesRaw {n} 100"), (t + hold, f"notesRaw {n} 0")]


def note(ev, t, ch, n, dur, br=100):
    ev += [(t, f"eng-in 0 {ch} {n} 100"), (t + 1, f"eng-in 4 {ch} 11 {br}"), (t + dur, f"eng-in 0 {ch} {n} 0")]


def cents(fr, ref):
    return 1200 * np.log2(fr / ref) if fr > 0 else 9999


# 1. the patch loads without errors
log = run(P, [(300, "knob1 0.5")])
check("loads without errors", not errors(log), "; ".join(errors(log)[:3]))

# reference pitch of A3 with the default tuning (Halo is a clean, sine-based engine)
ref = None

# 2. every engine sounds, at the right pitch, and reacts to breath
for i, name in enumerate(ENGINES):
    ev = [(100, "notesRaw 69 100"), (150, "notesRaw 69 0"), (200, "knob1 0.99"), (300, f"knob1 {(i + 0.5) / 6}"),
          (900, "notesRaw 60 100"), (950, "notesRaw 60 0")]
    note(ev, 1500, 2, 57, 1500, 40)
    note(ev, 3500, 2, 57, 1500, 127)
    ev.append((5500, "knob2 0.5"))
    log = run(P, ev)
    x = audio(P).mean(1)
    soft, loud = rms(x, 2.2, 2.9), rms(x, 4.2, 4.9)
    fr = f0(x[int(4.2 * SR):int(4.9 * SR)], lo=40, hi=330)
    if ref is None:
        ref = fr
    # octave-equivalent (Under plays an octave or two down)
    dev = min((cents(fr, ref) - k) for k in (0, -1200, -2400) if abs(cents(fr, ref) - k) == min(
        abs(cents(fr, ref) - kk) for kk in (0, -1200, -2400)))
    ok = not errors(log) and loud > 0.02 and loud > soft * 1.2 and abs(dev) < 30
    check(f"engine {name}", ok, f"soft {soft:.3f} loud {loud:.3f} pitch {dev:+.0f} c")

# 3. a repeated note-on never leaves a voice stuck (looper clear)
ev = [(500, "eng-proc 0 18 60 100"), (501, "eng-proc 4 18 11 100"), (800, "eng-proc 0 18 60 100"),
      (1200, "eng-proc 0 18 60 0"), (1300, "eng-loop-clear bang"), (6000, "knob1 0.3")]
run(P, ev)
x = audio(P).mean(1)
check("no stuck notes after looper clear", rms(x, 5.0, 5.5) < 0.002, f"rms at 5 s {rms(x, 5.0, 5.5):.4f}")

# 4. switching engines while playing: a short fade (no gap, no click), held notes keep sounding
ev = [(300, "eng-in 0 2 57 100"), (301, "eng-in 4 2 11 100"), (500, "notesRaw 69 100"), (550, "notesRaw 69 0"),
      (600, "knob1 0.79")]
for i, t in enumerate(range(1500, 9000, 1200)):
    ev.append((t, f"knob1 {((i % 6) + 0.5) / 6}"))
ev += [(9500, "eng-in 0 2 57 0"), (10000, "knob2 0.5")]
log = run(P, ev)
x = audio(P).mean(1)
lv = np.array([rms(x, t, t + 0.01) for t in np.arange(1.0, 9.4, 0.01)])
quiet = lv < 0.1 * np.median(lv)
longest = max((len(r) for r in "".join("1" if q else "0" for q in quiet).split("0")), default=0) * 10
check("engine switch while playing", not errors(log) and longest <= 60, f"longest dip {longest} ms")

# 5. MIDI looper records and plays back
ev = []
ev += [(500, "aux 1"), (550, "aux 0")]
note(ev, 600, 2, 60, 500)
ev += [(2000, "aux 1"), (2050, "aux 0"), (6000, "knob2 0.5")]
run(P, ev)
x = audio(P).mean(1)
check("MIDI looper plays back", rms(x, 3.5, 4.2) > 0.02, f"rms {rms(x, 3.5, 4.2):.3f}")

# 6. audio looper: record, play back (after the live note), overdub at 2x, undo  (delay and reverb off)
ev = []
key(ev, 200, 64)
ev += [(300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0")]
key(ev, 400, 60)
key(ev, 500, 81)
note(ev, 600, 2, 60, 600)
key(ev, 2500, 81)
ev += [(3000, "notesRaw 81 100"), (3030, "knob1 0.5"), (3040, "knob1 0.78"), (3080, "notesRaw 81 0")]
key(ev, 3500, 81)
note(ev, 3700, 3, 67, 300)
key(ev, 4600, 81)
ev += [(6000, "notesRaw 81 100"), (6030, "knob1 0.5"), (6040, "knob1 0.5"), (6080, "notesRaw 81 0")]
key(ev, 9000, 82)
ev.append((11500, "knob2 0.5"))
log = run(P, ev)
x = audio(P).mean(1)
check("audio looper plays back", rms(x, 2.6, 3.0) > 0.02, f"rms {rms(x, 2.6, 3.0):.3f}")
g3 = [f0(x[int(t * SR):int((t + 0.1) * SR)], lo=150, hi=600) for t in np.arange(6.2, 8.9, 0.1)]
has_g3 = any(abs(cents(fr, 196.0)) < 70 for fr in g3)
check("audio overdub keeps its speed (2x dub plays an octave down at 1x)", has_g3)
after = [f0(x[int(t * SR):int((t + 0.1) * SR)], lo=150, hi=600) for t in np.arange(9.2, 11.2, 0.1)]
check("audio looper undo", not any(abs(cents(fr, 196.0)) < 70 for fr in after) and rms(x, 9.2, 11.2) > 0.01)

# 7. tuning library sends a tuning while the loop keeps playing
ev = [(500, "aux 1"), (550, "aux 0")]
note(ev, 600, 2, 60, 1700)
ev += [(2500, "aux 1"), (2550, "aux 0"), (3000, "notesRaw 61 100"), (3050, "notesRaw 61 0"),
       (3200, "knob1 0.05"), (3400, "aux 1"), (3450, "aux 0"), (8000, "knob2 0.5")]
log = run(P, ev)
x = audio(P).mean(1)
sent = [l for l in log.splitlines() if l.startswith("dmx-sent")]
check("tuning sent while looping", len(sent) >= 96 and rms(x, 3.5, 4.2) > 0.02, f"{len(sent)} MIDI events")

# 8. no clicks while overdubbing the audio looper or afterwards (bursts above 8 kHz; Halo, delay/reverb off)
def hf_clicks(x, a, b, db=18.0):
    seg = x[int(a * SR):int(b * SR)]
    S = np.fft.rfft(seg); f = np.fft.rfftfreq(len(seg), 1 / SR); S[f < 8000] = 0
    hp = np.fft.irfft(S, len(seg)); w = 220
    e = np.array([np.sum(hp[i:i + w] ** 2) for i in range(0, len(hp) - w, w)]) + 1e-12
    return [round(a + i * w / SR, 3) for i in range(2, len(e))
            if 10 * np.log10(e[i] / np.median(e[max(0, i - 40):i + 40])) > db and e[i] > 1e-7]
ev = []
key(ev, 200, 64)
ev += [(300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0")]
key(ev, 400, 60)
ev += [(430, "notesRaw 69 100"), (440, "notesRaw 69 0"), (450, "knob1 0.99"), (460, f"knob1 {0.5 / 6}"),
       (470, "notesRaw 60 100"), (480, "notesRaw 60 0")]
key(ev, 1500, 81)
note(ev, 1520, 2, 57, 2100, 90)
key(ev, 3600, 81)
key(ev, 4000, 81)
note(ev, 4050, 3, 64, 6500, 90)
key(ev, 10800, 81)
ev.append((15000, "knob2 0.5"))
run(P, ev)
x = audio(P).mean(1)
cl = hf_clicks(x, 3.7, 14.9)
check("no clicks in audio overdubs or at the loop seam", not cl, f"clicks at {cl[:5]}" if cl else "")

print()
if failures:
    print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
    sys.exit(1)
print("All checks passed.")
