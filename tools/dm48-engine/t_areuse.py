"""Audio loop: after a clear, an overdub that reuses an old layer slot must not play the old layer's audio."""
import sys, numpy as np
from harness import run, audio
P = sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"; SR = 44100
def rms(x, a, b): s = x[int(a*SR):int(b*SR)]; return float(np.sqrt((s**2).mean()))
def tap(ev, t, hold=60): ev += [(t, "notesRaw 81 100"), (t + hold, "notesRaw 81 0")]
def areuse_test(P):
    ev = [(200, "notesRaw 64 100"), (210, "notesRaw 64 0"), (300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0"),
          (400, "notesRaw 60 100"), (410, "notesRaw 60 0")]
    tap(ev, 600)                                                    # REC
    ev += [(700, "eng-in 0 2 57 100"), (701, "eng-in 4 2 11 100"), (1300, "eng-in 0 2 57 0")]
    tap(ev, 2000); tap(ev, 2500)                                    # PLAY, DUB
    ev += [(2600, "eng-in 0 2 64 100"), (2601, "eng-in 4 2 11 100"), (3300, "eng-in 0 2 64 0")]
    tap(ev, 4100)                                                   # PLAY
    tap(ev, 5000, 1300)                                             # hold: clear
    tap(ev, 7000); tap(ev, 8000); tap(ev, 8500); tap(ev, 9400)      # silent REC, PLAY, DUB (nothing played), PLAY
    ev.append((11000, "knob2 0.5"))
    log = run(P, ev); x = audio(P).mean(1)
    return rms(x, 4.2, 4.9), rms(x, 8.0, 10.9)
if __name__ == "__main__":
    print("old loop %.3f   new silent loop + overdub %.4f" % areuse_test(P))
