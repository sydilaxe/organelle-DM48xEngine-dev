"""Freeze (high C): tap = capture a layer that holds after the note ends; taps stack; hold = all off."""
import sys, numpy as np
from harness import run, audio, f0
P = sys.argv[1] if len(sys.argv) > 1 else "../DM48 Engine"; SR = 44100
def rms(x, a, b): s = x[int(a*SR):int(b*SR)]; return float(np.sqrt((s**2).mean()))
def band(x, a, b, f):
    s = x[int(a*SR):int(b*SR)] * np.hanning(int(b*SR) - int(a*SR)); S = np.abs(np.fft.rfft(s)); fr = np.fft.rfftfreq(len(s), 1/SR)
    return float(S[(fr > f * 0.98) & (fr < f * 1.02)].max())
def freeze_test(P, taps=2):
    # delay and reverb off; A3 then E4, a tap during each; hold at 9 s
    ev = [(200, "notesRaw 64 100"), (210, "notesRaw 64 0"), (300, "knob3 0.5"), (310, "knob3 0"), (320, "knob4 0.5"), (330, "knob4 0"),
          (400, "notesRaw 60 100"), (410, "notesRaw 60 0")]
    notes = [57, 64, 60, 67, 62, 69, 65]
    for k in range(taps):
        t = 600 + k * 1200
        ev += [(t, f"eng-in 0 2 {notes[k]} 100"), (t + 1, "eng-in 4 2 11 100"), (t + 900, f"eng-in 0 2 {notes[k]} 0"),
               (t + 100, "notesRaw 72 100"), (t + 160, "notesRaw 72 0")]
    th = 600 + taps * 1200 + 1500
    ev += [(th, "notesRaw 72 100"), (th + 900, "notesRaw 72 0"), (th + 4000, "knob2 0.5")]
    log = run(P, ev); x = audio(P).mean(1)
    return x, log, th / 1000
if __name__ == "__main__":
    x, log, th = freeze_test(P, 2)
    print("errors", [l for l in log.splitlines() if "rror" in l][:3])
    print("toasts", [l for l in log.splitlines() if "Freeze" in l][:8])
    for a in (1.3, 2.6, 3.4, th - 0.5, th + 1.0, th + 3.0):
        print(f"t={a:.1f} rms {rms(x, a, a + 0.4):.4f}  A3 {band(x, a, a + 0.4, 220):.1f}  E4 {band(x, a, a + 0.4, 329.6):.1f}")
