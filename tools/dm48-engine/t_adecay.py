"""Audio loop decay (hold high A + knob 4): the loop fades smoothly pass after pass, and a fully faded layer is freed."""
import sys, numpy as np
from harness import run, audio
P = sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"; SR = 44100
def rms(x, a, b): s = x[int(a*SR):int(b*SR)]; return float(np.sqrt((s**2).mean()))
def adecay_test(P, knob):
    # delay/reverb off, record a 1 s drone loop, then set the decay
    ev = [(200, "notesRaw 64 100"), (210, "notesRaw 64 0"), (300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0"),
          (400, "notesRaw 60 100"), (410, "notesRaw 60 0"),
          (600, "notesRaw 81 100"), (660, "notesRaw 81 0"),
          (700, "eng-in 0 2 57 100"), (701, "eng-in 4 2 11 100"), (1640, "eng-in 0 2 57 0"),
          (1600, "notesRaw 81 100"), (1660, "notesRaw 81 0"),
          (2000, "notesRaw 81 100"), (2030, "knob4 0.5"), (2040, f"knob4 {knob}"), (2080, "notesRaw 81 0"),
          (9000, "knob2 0.5")]
    log = run(P, ev); x = audio(P).mean(1)
    return [rms(x, t, t + 0.25) for t in np.arange(2.0, 8.75, 0.25)], log
if __name__ == "__main__":
    for k in (0.0, 0.3, 1.0):
        lv, log = adecay_test(P, k)
        print(k, " ".join(f"{v:.3f}" for v in lv), [l for l in log.splitlines() if "rror" in l][:2])
