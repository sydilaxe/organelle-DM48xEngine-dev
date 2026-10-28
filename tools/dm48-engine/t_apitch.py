"""Audio loop pitch is continuous: +3.5 semitones plays 3.5 st up; turning the knob doesn't click."""
import sys, numpy as np
from harness import run, audio, f0
SR = 44100
def key(ev, t, n, h=60): ev += [(t, f"notesRaw {n} 100"), (t + h, f"notesRaw {n} 0")]
def apitch_test(P, st=3.5):
    v = 0.52 + st * 0.96 / 24
    ev = [(100, "notesRaw 69 100"), (150, "notesRaw 69 0"), (200, "knob1 0.99"), (300, f"knob1 {1.5 / 7}"),   # Halo
          (400, "notesRaw 60 100"), (450, "notesRaw 60 0"), (500, "notesRaw 64 100"), (510, "notesRaw 64 0"),
          (520, "knob3 0.5"), (530, "knob3 0"), (540, "knob4 0.5"), (550, "knob4 0")]                     # dry
    key(ev, 1000, 81)
    ev += [(1020, "eng-in 0 2 57 100"), (1021, "eng-in 4 2 11 100"), (3200, "eng-in 0 2 57 0")]
    key(ev, 3000, 81)
    ev += [(5000, "notesRaw 81 100"), (5030, "knob2 0.5")]
    for k in range(21):                                        # sweep up slowly to the target
        ev.append((5050 + k * 20, f"knob2 {0.5 + (v - 0.5) * k / 20:.4f}"))
    ev += [(5600, "notesRaw 81 0"), (9000, "knob3 0.3")]
    run(P, ev); x = audio(P).mean(1)
    a = f0(x[int(3.6 * SR):int(4.6 * SR)], lo=100, hi=500)
    b = f0(x[int(6.5 * SR):int(7.5 * SR)], lo=100, hi=500)
    return 12 * np.log2(b / a) if a > 0 and b > 0 else None
if __name__ == "__main__":
    print("shift", apitch_test(sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"))


def aspeed_test(P, knob=0.75):
    """audio loop speed is continuous: knob -> speed s, the loop's pitch moves by 12*log2(s) (tape)"""
    sp = 2 ** ((knob - 0.56) / 0.44 * 2)
    ev = [(100, "notesRaw 69 100"), (150, "notesRaw 69 0"), (200, "knob1 0.99"), (300, f"knob1 {1.5 / 7}"),
          (400, "notesRaw 60 100"), (450, "notesRaw 60 0"), (500, "notesRaw 64 100"), (510, "notesRaw 64 0"),
          (520, "knob3 0.5"), (530, "knob3 0"), (540, "knob4 0.5"), (550, "knob4 0")]
    key(ev, 1000, 81)
    ev += [(1020, "eng-in 0 2 57 100"), (1021, "eng-in 4 2 11 100"), (3200, "eng-in 0 2 57 0")]
    key(ev, 3000, 81)
    ev += [(5000, "notesRaw 81 100"), (5030, "knob1 0.5"), (5050, f"knob1 {knob}"), (5300, "notesRaw 81 0"), (9000, "knob3 0.3")]
    run(P, ev); x = audio(P).mean(1)
    a = f0(x[int(3.6 * SR):int(4.6 * SR)], lo=100, hi=600)
    b = f0(x[int(6.5 * SR):int(7.5 * SR)], lo=100, hi=600)
    return (12 * np.log2(b / a) if a > 0 and b > 0 else None), 12 * np.log2(sp)
