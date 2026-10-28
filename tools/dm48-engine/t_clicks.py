"""Click detector: counts sudden jumps in the output that a smooth signal wouldn't make.
A click = |second difference| far above the local level (median of the neighbourhood)."""
import sys, warnings, numpy as np
warnings.filterwarnings("ignore"); sys.path.insert(0,'.')
from harness import run, audio
P="../DM48 Engine"; SR=44100

def clicks(x, a, b, db=18.0):
    """times where the energy above 8 kHz jumps more than `db` above its local median (5 ms windows)"""
    s = x[int(a*SR):int(b*SR)]
    S = np.fft.rfft(s); f = np.fft.rfftfreq(len(s), 1/SR); S[f < 8000] = 0
    hp = np.fft.irfft(S, len(s))
    w = 220
    e = np.array([np.sum(hp[i:i+w]**2) for i in range(0, len(hp) - w, w)]) + 1e-12
    out = []
    for i in range(2, len(e)):          # (the first windows have no left context)
        lo, hi = max(0, i - 40), min(len(e), i + 40)
        if 10*np.log10(e[i] / np.median(e[lo:hi])) > db and e[i] > 1e-7:
            t = round(a + i*w/SR, 3)
            if not out or t - out[-1] > 0.02: out.append(t)
    return out

def key(ev, t, n, hold=60): ev += [(t, f"notesRaw {n} 100"), (t + hold, f"notesRaw {n} 0")]
def note(ev, t, ch, n, dur, br=100): ev += [(t, f"eng-in 0 {ch} {n} 100"), (t + 1, f"eng-in 4 {ch} 11 {br}"), (t + dur, f"eng-in 0 {ch} {n} 0")]
def fx_off(ev):
    key(ev, 200, 64); ev += [(300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0")]; key(ev, 400, 60)

which = sys.argv[1:] or ["engine", "dub"]
if "engine" in which:
    # a held note while switching engines several times
    ev=[]; fx_off(ev)
    ev += [(500, "notesRaw 69 100"), (550, "notesRaw 69 0"), (560, "knob1 0.99"), (570, f"knob1 {1.5/7}"), (580, "notesRaw 60 100"), (590, "notesRaw 60 0"),
           (600, "eng-in 0 2 57 100"), (601, "eng-in 4 2 11 100"), (700, "notesRaw 69 100"), (750, "notesRaw 69 0"), (800, "knob1 0.79")]
    for i, t in enumerate(range(2000, 9000, 1500)):
        ev.append((t, f"knob1 {((i % 7) + 0.5) / 7}"))
    ev += [(9500, "eng-in 0 2 57 0"), (10000, "knob2 0.5")]
    run(P, ev); x = audio(P).mean(1)
    print("engine switches -> clicks at:", clicks(x, 1.0, 9.4))
if "dub" in which:
    # a sustained base take, then a long sustained overdub over several passes
    ev=[]; fx_off(ev)
    ev += [(430, "notesRaw 69 100"), (440, "notesRaw 69 0"), (450, "knob1 0.99"), (460, f"knob1 {1.5/7}"), (470, "notesRaw 60 100"), (480, "notesRaw 60 0")]  # Halo
    key(ev, 1500, 81); note(ev, 1520, 2, 57, 2100, 90); key(ev, 3600, 81)          # base: A3 held through the take
    key(ev, 4000, 81); note(ev, 4050, 3, 64, 6500, 90); key(ev, 10800, 81)         # dub: E4 for ~3 passes
    ev.append((15000, "knob2 0.5"))
    run(P, ev); x = audio(P).mean(1)
    print("loop only                clicks at:", clicks(x, 3.7, 4.0))
    print("during dub               clicks at:", clicks(x, 4.1, 10.7))
    print("after dub (loop playing) clicks at:", clicks(x, 11.0, 14.9))

if "dubspeed" in which:
    for spd, v in (("2x", 0.78), ("reverse", 0.43)):
        ev=[]; fx_off(ev)
        ev += [(430, "notesRaw 69 100"), (440, "notesRaw 69 0"), (450, "knob1 0.99"), (460, f"knob1 {1.5/7}"), (470, "notesRaw 60 100"), (480, "notesRaw 60 0")]
        key(ev, 1500, 81); note(ev, 1520, 2, 57, 2100, 90); key(ev, 3600, 81)
        ev += [(3800, "notesRaw 81 100"), (3830, "knob1 0.5"), (3840, f"knob1 {v}"), (3880, "notesRaw 81 0")]
        key(ev, 4000, 81); note(ev, 4050, 3, 64, 4500, 90); key(ev, 8800, 81)
        ev.append((13000, "knob2 0.5"))
        run(P, ev); x = audio(P).mean(1)
        print(f"dub at {spd:8s} during: {clicks(x, 4.1, 8.7)}  after: {clicks(x, 9.0, 12.9)}")
