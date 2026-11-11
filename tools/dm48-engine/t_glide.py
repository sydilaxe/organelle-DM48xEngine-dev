"""Glide / legato checks (VOICE page), Halo engine. Returns pitch tracks; used by ci_check.py too."""
import sys, numpy as np
from harness import run, audio, f0, eng_knob
SR = 44100


def setup(mode, glide, when, frm):
    """Halo engine, then VOICE page: knob1 mode, knob2 glide (relative knob: 0 first), knob3 when, knob4 from;
    then delay and reverb off."""
    return [(100, "notesRaw 69 100"), (150, "notesRaw 69 0"), (200, "knob1 0.99"), (300, f"knob1 {eng_knob('halo')}"),
            (400, "notesRaw 66 100"), (450, "notesRaw 66 0"),
            (500, f"knob1 {0.9 if mode else 0.1}"), (520, "knob2 0"), (540, f"knob2 {glide}"),
            (560, f"knob3 {0.9 if when else 0.1}"), (580, f"knob4 {0.9 if frm else 0.1}"),
            # FX page: delay and reverb off - their tails hold the previous pitch and can fool the pitch tracker
            (600, "notesRaw 64 100"), (650, "notesRaw 64 0"), (700, "knob3 1"), (710, "knob3 0"),
            (720, "knob4 1"), (730, "knob4 0")]


def note(ev, t, ch, n, dur):
    ev += [(t, f"eng-in 0 {ch} {n} 100"), (t + 1, f"eng-in 4 {ch} 11 100"), (t + dur, f"eng-in 0 {ch} {n} 0")]


def track(x, a, b, step=0.02):
    out = []
    for t in np.arange(a, b, step):
        fr = f0(x[int(t * SR):int((t + 0.04) * SR)], lo=150, hi=600)
        out.append(round(12 * np.log2(fr / 440) + 69, 1) if fr > 0 else None)
    return out


def glide_tests(P):
    res = {}
    # poly, glide 500 ms always, from last: A3, gap, A4 -> glides up over ~0.5 s
    ev = setup(0, 0.5, 0, 1); note(ev, 1000, 2, 57, 800); note(ev, 2000, 3, 69, 1500); ev.append((4000, "knob3 0.1"))
    run(P, ev); res["poly"] = track(audio(P).mean(1), 2.0, 3.0)
    # poly, legato only: no overlap -> jumps
    ev = setup(0, 0.5, 1, 1); note(ev, 1000, 2, 57, 800); note(ev, 2000, 3, 69, 1500); ev.append((4000, "knob3 0.1"))
    run(P, ev); res["gap"] = track(audio(P).mean(1), 2.0, 3.0)
    # mono legato: hold A3, press A4 -> glide up; release A4 -> glide back to A3
    ev = setup(1, 0.5, 1, 1); note(ev, 1000, 2, 57, 3000); note(ev, 2000, 3, 69, 1000); ev.append((4500, "knob3 0.1"))
    run(P, ev); res["mono"] = track(audio(P).mean(1), 1.5, 4.0)
    return res


if __name__ == "__main__":
    for k, tr in glide_tests(sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine").items():
        print(k, " ".join(str(p) for p in tr))
