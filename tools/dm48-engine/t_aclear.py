"""Audio loop: record, play, then clear by holding high A -> must be silent afterwards."""
import sys, numpy as np
from harness import run, audio
P = sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"; SR = 44100
def rms(x, a, b): s = x[int(a*SR):int(b*SR)]; return float(np.sqrt((s**2).mean()))
def aclear_test(P, post=False, hold_ms=1200):
    ev = [(200, "notesRaw 64 100"), (210, "notesRaw 64 0"), (300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0"),
          (400, "notesRaw 60 100"), (410, "notesRaw 60 0")]
    if post:
        ev += [(450, "notesRaw 83 100"), (470, "knob1 0.9"), (480, "knob1 1.0"), (500, "notesRaw 83 0")]
    ev += [(600, "notesRaw 81 100"), (660, "notesRaw 81 0"),
           (700, "eng-in 0 2 57 100"), (701, "eng-in 4 2 11 100"), (1300, "eng-in 0 2 57 0"),
           (2000, "notesRaw 81 100"), (2060, "notesRaw 81 0"),
           (4000, "notesRaw 81 100"), (4000 + hold_ms, "notesRaw 81 0"), (8000, "knob2 0.5")]
    log = run(P, ev); x = audio(P)
    return rms(x.mean(1), 2.5, 3.5), rms(x.mean(1), 5.8, 7.8), x
if __name__ == "__main__":
    for post in (False, True):
        play, after, x = aclear_test(P, post)
        seg = x[int(6*SR):int(6.1*SR), 0]
        print("post" if post else "pre", f"playing {play:.3f}  after clear {after:.4f}", "peak", float(np.abs(x[int(5.5*SR):,:]).max()))
