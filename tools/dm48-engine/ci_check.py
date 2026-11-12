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
from harness import run, audio, f0, ENGINE_NAMES  # noqa: E402

P = sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"
SR = 44100
ENGINES = ENGINE_NAMES   # sorted, as on the ENGINE knob
NE = len(ENGINES)
HALO = (ENGINES.index("halo") + 0.5) / NE
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
for name in sorted(ENGINES, key=lambda n: n != "halo"):     # Halo first: it sets the reference pitch
    i = ENGINES.index(name)
    ev = [(100, "notesRaw 69 100"), (150, "notesRaw 69 0"), (200, "knob1 0.99"), (300, f"knob1 {(i + 0.5) / NE}"),
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

# 2b. every mode of the engines with mode knobs sounds (Hybrid: Source x Body, Doom: Chain)
def knob_to(ev, t, k, v):
    """PLAY knobs pick up relatively: push to 1, then 0, then the value"""
    ev += [(t, f"knob{k} 1.0"), (t + 5, f"knob{k} 0.0"), (t + 10, f"knob{k} {v}")]


for name, combos in (("hybrid", [(a, b) for a in range(4) for b in range(4)]), ("doom", [(a, None) for a in range(4)])):
    i = ENGINES.index(name)
    quiet = []
    for a, b in combos:
        ev = [(100, "notesRaw 69 100"), (150, "notesRaw 69 0"), (200, "knob1 0.99"), (300, f"knob1 {(i + 0.5) / NE}"),
              (900, "notesRaw 60 100"), (950, "notesRaw 60 0")]
        knob_to(ev, 1500, 1, (a + 0.5) / 4)              # after the engine switch (it restores the engine's knobs)
        if b is not None:
            knob_to(ev, 1550, 2, (b + 0.5) / 4)
        note(ev, 2000, 2, 57, 1200, 110)
        ev.append((3500, "knob3 0.3"))
        log = run(P, ev)
        lvl = rms(audio(P).mean(1), 2.5, 3.1)
        if errors(log) or not 0.03 < lvl < 0.5:
            quiet.append(f"{a}/{b}: {lvl:.3f}")
    check(f"every {name} mode sounds", not quiet, "; ".join(quiet[:4]))

# 3. a repeated note-on never leaves a voice stuck (looper clear)
ev = [(500, "eng-proc 0 18 60 100"), (501, "eng-proc 4 18 11 100"), (800, "eng-proc 0 18 60 100"),
      (1200, "eng-proc 0 18 60 0"), (1300, "eng-loop-clear bang"), (6000, "knob1 0.3")]
run(P, ev)
x = audio(P).mean(1)
check("no stuck notes after looper clear", rms(x, 5.0, 5.5) < 0.002, f"rms at 5 s {rms(x, 5.0, 5.5):.4f}")

# 3b. clearing the MIDI looper silences loop notes that are still on (first take and an overdub layer)
ev = [(500, "eng-proc 0 18 60 100"), (510, "eng-proc 0 35 64 100"), (1300, "eng-loop-clear bang"), (5000, "knob1 0.3")]
run(P, ev)
x = audio(P).mean(1)
check("MIDI looper clear silences held loop notes", rms(x, 0.9, 1.2) > 0.02 and rms(x, 4.0, 4.5) < 0.002,
      f"rms at 4 s {rms(x, 4.0, 4.5):.4f}")

# 3c. a bend sent before the MIDI loop was recorded is part of the loop (the loop plays at the live pitch)
ev = [(300, "eng-in 1 3 8400 0"), (500, "aux 1"), (550, "aux 0"), (600, "eng-in 0 3 57 100"), (601, "eng-in 4 3 11 100"),
      (1100, "eng-in 0 3 57 0"), (2000, "aux 1"), (2050, "aux 0"), (4500, "knob2 0.5")]
run(P, ev)
x = audio(P).mean(1)
live_, loop_ = f0(x[int(0.8 * SR):int(1.0 * SR)], lo=100, hi=500), f0(x[int(3.8 * SR):int(4.0 * SR)], lo=100, hi=500)
check("MIDI loop keeps a bend sent before recording", abs(cents(loop_, live_)) < 10, f"live {live_:.1f} Hz loop {loop_:.1f} Hz")

# 4. switching engines while playing: a short fade (no gap, no click), held notes keep sounding
ev = [(300, "eng-in 0 2 57 100"), (301, "eng-in 4 2 11 100"), (500, "notesRaw 69 100"), (550, "notesRaw 69 0"),
      (600, "knob1 0.79")]
for i, t in enumerate(range(1500, 9000, 1200)):
    ev.append((t, f"knob1 {((i % NE) + 0.5) / NE}"))
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
ev += [(430, "notesRaw 69 100"), (440, "notesRaw 69 0"), (450, "knob1 0.99"), (460, f"knob1 {HALO}"),
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

# 9. clearing the audio loop (hold high A) leaves silence, Pre and Post (no stuck block repeating)
from t_aclear import aclear_test
for post in (False, True):
    play, after, _ = aclear_test(P, post)
    check(f"audio loop clear is silent ({'Post' if post else 'Pre'})", play > 0.02 and after < 0.001,
          f"playing {play:.3f} after clear {after:.4f}")

# 9b. audio loop decay: off at the left; at the right the loop fades smoothly to silence within a few passes
from t_adecay import adecay_test
lv0, _ = adecay_test(P, 0.0)
lv1, _ = adecay_test(P, 1.0)
steps = [b / a for a, b in zip(lv1[2:16], lv1[3:17]) if a > 0.004]
p0, p5 = np.mean(lv0[0:4]), np.mean(lv0[20:24])        # whole 1 s passes, 5 s apart
check("audio loop decay off keeps the level", abs(p5 / p0 - 1) < 0.05, f"{p0:.3f} -> {p5:.3f}")
check("audio loop decay fades smoothly to silence", lv1[-1] < 0.001 and min(steps) > 0.4,
      f"end {lv1[-1]:.4f}, steepest 0.25 s step x{min(steps):.2f}")

from t_adubdecay import adubdecay_test
e_ = adubdecay_test(P)
check("audio loop decay continues while overdubbing", all(0.3 < b / a < 0.5 for a, b in zip(e_, e_[1:])),
      " ".join(f"{b / a:.2f}" for a, b in zip(e_, e_[1:])))
from t_areuse import areuse_test
old_, new_ = areuse_test(P)
check("an overdub after a clear never plays the old loop", old_ > 0.02 and new_ < 0.001, f"{new_:.4f}")

# 9c. freeze (high C): taps stack layers that hold after the notes end, the 7th fades the 1st, hold = all off
from t_freeze import freeze_test, band as fband
x, log, th = freeze_test(P, 2)
held = fband(x, 3.4, 4.2, 110.0) > 20 and fband(x, 3.4, 4.2, 164.8) > 20      # A2 and E3 (DM48 plays them an octave down)
check("freeze holds two stacked layers", held and not errors(log),
      f"A {fband(x, 3.4, 4.2, 110.0):.0f} E {fband(x, 3.4, 4.2, 164.8):.0f}")
check("freeze long hold fades everything out", rms(x, th + 3.0, th + 3.5) < 0.001, f"{rms(x, th + 3.0, th + 3.5):.4f}")
x, log, th = freeze_test(P, 7)
check("7th freeze fades out the 1st layer", fband(x, 9.6, 10.4, 110.0) < 5 and fband(x, 9.6, 10.4, 164.8) > 20,
      f"first {fband(x, 9.6, 10.4, 110.0):.0f} second {fband(x, 9.6, 10.4, 164.8):.0f}")

# 10. audio loop pitch is continuous (+3.5 semitones)
from t_apitch import apitch_test
sh_ = apitch_test(P)
check("audio loop pitch is continuous (+3.5 st)", sh_ is not None and abs(sh_ - 3.5) < 0.15, f"{sh_:+.2f} st" if sh_ else "")

from t_apitch import aspeed_test
got_, want_ = aspeed_test(P)
check("audio loop speed is continuous (1.82x, tape pitch)", got_ is not None and abs(got_ - want_) < 0.15,
      f"{got_:+.2f} st, expected {want_:+.2f}" if got_ else "")
got_, want_ = aspeed_test(P, knob=0.44 - 0.44 / 6)       # left of centre: slower (0.5x, an octave down)
check("audio loop speed left of centre slows down (0.5x)", got_ is not None and abs(got_ - want_) < 0.15,
      f"{got_:+.2f} st, expected {want_:+.2f}" if got_ else "")

# 11. glide and legato (VOICE page)
from t_glide import glide_tests
g = glide_tests(P)
mid = lambda tr, i: tr[i] if tr[i] is not None else 0
check("poly glide (A3 -> A4 over 0.5 s)", 61 < mid(g["poly"], 12) < 65 and abs(mid(g["poly"], 40) - 68.9) < 0.3,
      f"at 0.24 s {mid(g['poly'], 12)}")
check("glide legato-only: no glide without overlap", abs(mid(g["gap"], 5) - 68.9) < 0.3)
check("mono legato glides up and back", 61 < mid(g["mono"], 37) < 65 and abs(mid(g["mono"], 60) - 68.9) < 0.3
      and 61 < mid(g["mono"], 87) < 65 and abs(mid(g["mono"], 120) - 56.9) < 0.3,
      f"{mid(g['mono'], 37)} {mid(g['mono'], 60)} {mid(g['mono'], 87)} {mid(g['mono'], 120)}")

print()
if failures:
    print(f"{len(failures)} check(s) failed: {', '.join(failures)}")
    sys.exit(1)
print("All checks passed.")
