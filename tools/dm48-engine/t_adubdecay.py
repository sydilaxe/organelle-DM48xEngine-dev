"""Audio loop decay keeps going during a long overdub: what was overdubbed fades pass by pass while still dubbing."""
import sys, numpy as np
from harness import run, audio
P = sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"; SR = 44100
def tap(ev, t, hold=60): ev += [(t, "notesRaw 81 100"), (t + hold, "notesRaw 81 0")]
def band(x, a, b, f):
    s = x[int(a*SR):int(b*SR)] * np.hanning(int(b*SR) - int(a*SR)); S = np.abs(np.fft.rfft(s)); fr = np.fft.rfftfreq(len(s), 1/SR)
    return float(S[(fr > f * 0.97) & (fr < f * 1.03)].max())
def adubdecay_test(P, knob=1.0):
    ev = [(200, "notesRaw 64 100"), (210, "notesRaw 64 0"), (300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0"),
          (400, "notesRaw 60 100"), (410, "notesRaw 60 0")]
    tap(ev, 600)                                                    # REC 1 s: A3
    ev += [(650, "eng-in 0 2 57 100"), (651, "eng-in 4 2 11 100"), (1550, "eng-in 0 2 57 0")]
    tap(ev, 1600)                                                   # PLAY
    ev += [(1700, "notesRaw 81 100"), (1730, "knob4 0.5"), (1740, f"knob4 {knob}"), (1780, "notesRaw 81 0")]
    tap(ev, 2000)                                                   # DUB (stays on): E4 in the first pass only
    ev += [(2100, "eng-in 0 3 64 100"), (2101, "eng-in 4 3 11 100"), (2900, "eng-in 0 3 64 0")]
    ev.append((9000, "knob2 0.5"))
    log = run(P, ev); x = audio(P).mean(1)
    # the loop runs ~1 s passes from 1.6 s; E4 energy in each later pass while still overdubbing
    return [band(x, 1.6 + k + 0.15, 1.6 + k + 0.85, 329.6) for k in range(2, 7)]
if __name__ == "__main__":
    e = adubdecay_test(P)
    print(" ".join(f"{v:.1f}" for v in e), " ratios", " ".join(f"{b / a:.2f}" for a, b in zip(e, e[1:])))
